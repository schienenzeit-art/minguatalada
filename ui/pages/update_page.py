from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QTableWidget, QTableWidgetItem,
    QTabWidget, QMessageBox, QProgressDialog, QFrame, QSizePolicy,
    QHeaderView, QGroupBox, QGridLayout,
)

from core.session import Session
from services.update_service import UpdateService, APP_VERSION
from ui.components.page_header import PageHeader

_ADMIN_ROLES = {"Admin"}


class _OnlineCheckWorker(QThread):
    """Prüft im Hintergrund auf Online-Updates."""
    done = pyqtSignal(object)  # UpdateCheckResult

    def __init__(self, update_service: UpdateService):
        super().__init__()
        self._svc = update_service

    def run(self):
        self.done.emit(self._svc.check_for_updates())


class _DownloadInstallWorker(QThread):
    """Lädt den Installer herunter und startet ihn. Fehler werden als Signal gemeldet."""
    progress = pyqtSignal(int, int)   # bytes_done, total (-1 = unbekannt)
    error    = pyqtSignal(str)

    def __init__(self, update_service: UpdateService, installer_url: str,
                 version: str, changelog: str, user_id: int | None):
        super().__init__()
        self._svc           = update_service
        self._installer_url = installer_url
        self._version       = version
        self._changelog     = changelog
        self._user_id       = user_id

    def run(self):
        try:
            self._svc.download_and_install(
                installer_url=self._installer_url,
                version=self._version,
                changelog=self._changelog,
                on_progress=lambda done, total: self.progress.emit(done, total),
                user_id=self._user_id,
            )
            # Wenn download_and_install() erfolgreich endet, ruft es sys.exit(0) — hier
            # wird nie Code erreicht. Nur im Fehlerfall springt der Worker zurück.
        except Exception as exc:
            self.error.emit(str(exc))


class _UpdateWorker(QThread):
    finished = pyqtSignal(bool, str, str)  # success, message, backup_path

    def __init__(self, update_service: UpdateService, package_path: Path, user_id: int):
        super().__init__()
        self.update_service = update_service
        self.package_path = package_path
        self.user_id = user_id

    def run(self):
        result = self.update_service.apply_update(self.package_path, user_id=self.user_id)
        self.finished.emit(result.success, result.message, result.backup_path)


class _BackupWorker(QThread):
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, update_service: UpdateService):
        super().__init__()
        self.update_service = update_service

    def run(self):
        try:
            path = self.update_service.create_backup()
            self.finished.emit(True, f"Backup erstellt:\n{path}")
        except Exception as e:
            self.finished.emit(False, f"Backup fehlgeschlagen:\n{e}")


class UpdatePage(QWidget):
    def __init__(self, update_service: UpdateService):
        super().__init__()
        self.update_service = update_service
        self._selected_package: Path | None = None
        self._validated_manifest = None
        self._worker = None
        self._online_check_result = None
        self._check_worker: _OnlineCheckWorker | None = None
        self._download_worker: _DownloadInstallWorker | None = None
        # Label-Referenzen mit None vorinitialisieren –
        # werden nur gesetzt wenn der Benutzer Admin-Rechte hat.
        self._lbl_version      = None
        self._lbl_last_update  = None
        self._lbl_backup_count = None
        self.setup_ui()
        # _refresh_status wird am Ende von setup_ui() aufgerufen,
        # sobald die Labels tatsächlich existieren.

    def setup_ui(self):
        self.setObjectName("updatePage")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        root.addWidget(PageHeader(
            title="Software-Update-Center",
            subtitle="Updates einspielen, Backups verwalten und Update-Verlauf einsehen.",
        ))

        # Zugriffsschutz
        user = Session.get_user() or {}
        if user.get("role_name", "") not in _ADMIN_ROLES:
            msg = QLabel(
                "Kein Zugriff. Diese Seite ist ausschliesslich "
                "für Systemadministratoren zugänglich."
            )
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet("color: #c0392b; font-size: 15px; padding: 40px;")
            root.addWidget(msg)
            return

        # Status-Karten
        root.addWidget(self._build_status_bar())

        # Tab-Widget
        tabs = QTabWidget()
        tabs.addTab(self._build_online_tab(), "Online-Update")
        tabs.addTab(self._build_local_update_tab(), "Manuell einspielen")
        tabs.addTab(self._build_history_tab(), "Update-Verlauf")
        tabs.addTab(self._build_backup_tab(), "Backup-Verwaltung")
        root.addWidget(tabs, 1)

        # Labels existieren jetzt – Status laden
        self._refresh_status()

    # ── Status-Karten ──────────────────────────────────────────────────────

    def _build_status_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(32)

        self._lbl_version = self._stat_item(layout, "Installierte Version", APP_VERSION)
        self._lbl_last_update = self._stat_item(layout, "Letztes Update", "–")
        self._lbl_backup_count = self._stat_item(layout, "Verfügbare Backups", "–")

        layout.addStretch()
        return frame

    @staticmethod
    def _stat_item(parent_layout: QHBoxLayout, label: str, value: str) -> QLabel:
        col = QVBoxLayout()
        col.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 11px; color: #888;")
        val = QLabel(value)
        val.setStyleSheet("font-size: 14px; font-weight: bold; color: #222;")
        col.addWidget(lbl)
        col.addWidget(val)
        parent_layout.addLayout(col)
        return val

    def _refresh_status(self):
        # Sicherheitsabfrage: Labels existieren nur im Admin-Modus
        if self._lbl_last_update is None or self._lbl_backup_count is None:
            return
        try:
            last = self.update_service.get_last_successful_update()
            if last:
                self._lbl_last_update.setText(
                    f"v{last['version']}  ({last['applied_at'][:10]})"
                )
            else:
                self._lbl_last_update.setText("Noch kein Update")

            backups = self.update_service.list_backups()
            self._lbl_backup_count.setText(str(len(backups)))
        except Exception:
            pass

    # ── Tab 1: Lokales Update ──────────────────────────────────────────────

    def _build_local_update_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Erklärungstext
        info = QLabel(
            "Wählen Sie ein Update-Paket (.mugala oder .zip) aus. "
            "Das Paket wird zunächst geprüft, bevor das Update eingespielt wird.\n"
            "Vor dem Update wird automatisch ein Datenbank-Backup erstellt."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #555; font-size: 12px;")
        layout.addWidget(info)

        # Dateiauswahl
        file_row = QHBoxLayout()
        self._lbl_selected_file = QLabel("Keine Datei ausgewählt")
        self._lbl_selected_file.setStyleSheet(
            "color: #777; font-style: italic; font-size: 12px; padding: 4px;"
        )
        self._lbl_selected_file.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        btn_browse = QPushButton("Paket auswählen...")
        btn_browse.setObjectName("SoftButton")
        btn_browse.clicked.connect(self._on_browse)
        file_row.addWidget(self._lbl_selected_file)
        file_row.addWidget(btn_browse)
        layout.addLayout(file_row)

        # Validierungsbereich
        group_validate = QGroupBox("Prüfungsergebnis")
        v_layout = QVBoxLayout(group_validate)
        self._txt_validation = QTextEdit()
        self._txt_validation.setReadOnly(True)
        self._txt_validation.setMaximumHeight(180)
        self._txt_validation.setPlaceholderText(
            "Wählen Sie ein Paket aus, um die Validierung zu starten."
        )
        self._txt_validation.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 12px;"
        )
        v_layout.addWidget(self._txt_validation)
        layout.addWidget(group_validate)

        # Changelog
        group_changelog = QGroupBox("Changelog")
        c_layout = QVBoxLayout(group_changelog)
        self._txt_changelog = QTextEdit()
        self._txt_changelog.setReadOnly(True)
        self._txt_changelog.setMaximumHeight(120)
        self._txt_changelog.setPlaceholderText("Wird nach Validierung angezeigt.")
        c_layout.addWidget(self._txt_changelog)
        layout.addWidget(group_changelog)

        layout.addStretch()

        # Aktions-Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_validate = QPushButton("Paket prüfen")
        self._btn_validate.setObjectName("SoftButton")
        self._btn_validate.setEnabled(False)
        self._btn_validate.clicked.connect(self._on_validate)

        self._btn_apply = QPushButton("UPDATE STARTEN")
        self._btn_apply.setObjectName("DangerButton")
        self._btn_apply.setEnabled(False)
        self._btn_apply.setMinimumWidth(180)
        self._btn_apply.setStyleSheet(
            "QPushButton#DangerButton {"
            "  background-color: #e74c3c; color: white; font-weight: bold;"
            "  padding: 8px 20px; border-radius: 4px; font-size: 13px;"
            "}"
            "QPushButton#DangerButton:hover { background-color: #c0392b; }"
            "QPushButton#DangerButton:disabled { background-color: #bbb; color: #888; }"
        )
        self._btn_apply.clicked.connect(self._on_apply_update)

        btn_row.addWidget(self._btn_validate)
        btn_row.addWidget(self._btn_apply)
        layout.addLayout(btn_row)

        return w

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Update-Paket auswählen",
            str(Path.home()),
            "Update-Pakete (*.mugala *.zip);;Alle Dateien (*)",
        )
        if path:
            self._selected_package = Path(path)
            self._lbl_selected_file.setText(path)
            self._lbl_selected_file.setStyleSheet(
                "color: #222; font-style: normal; font-size: 12px; padding: 4px;"
            )
            self._btn_validate.setEnabled(True)
            self._btn_apply.setEnabled(False)
            self._txt_validation.clear()
            self._txt_changelog.clear()
            self._validated_manifest = None

    def _on_validate(self):
        if not self._selected_package:
            return
        ok, msg, manifest = self.update_service.validate_package(self._selected_package)
        if ok:
            lines = [
                "PAKET GÜLTIG",
                f"  Version:          {manifest.version}",
                f"  Mindestversion:   {manifest.min_base_version or '–'}",
                f"  Maximalversion:   {manifest.max_base_version or '–'}",
                f"  Migrationen:      {len(manifest.migrations)}",
                f"  Installer:        {'Ja – ' + manifest.installer_file if manifest.installer_file else 'Nein (nur Migrationen)'}",
                f"  Datum:            {manifest.release_date or '–'}",
                f"  Neustart nötig:   {'Ja' if manifest.requires_restart else 'Nein'}",
            ]
            if manifest.migrations:
                lines.append("  Migrations-Dateien:")
                for m in manifest.migrations:
                    lines.append(f"    • {m}")
            self._txt_validation.setStyleSheet(
                "font-family: Consolas, monospace; font-size: 12px; color: #27ae60;"
            )
            self._txt_validation.setPlainText("\n".join(lines))
            self._txt_changelog.setPlainText(manifest.changelog or "Kein Changelog vorhanden.")
            self._validated_manifest = manifest
            self._btn_apply.setEnabled(True)
        else:
            self._txt_validation.setStyleSheet(
                "font-family: Consolas, monospace; font-size: 12px; color: #c0392b;"
            )
            self._txt_validation.setPlainText(f"FEHLER:\n{msg}")
            self._txt_changelog.clear()
            self._validated_manifest = None
            self._btn_apply.setEnabled(False)

    def _on_apply_update(self):
        if not self._selected_package or not self._validated_manifest:
            return

        manifest = self._validated_manifest
        confirm = QMessageBox(self)
        confirm.setWindowTitle("Update bestätigen")
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setText(
            f"<b>Update auf Version {manifest.version} einspielen?</b><br><br>"
            "Folgende Aktionen werden durchgeführt:<br>"
            f"&nbsp;&nbsp;1. Automatisches Datenbank-Backup<br>"
            f"&nbsp;&nbsp;2. {len(manifest.migrations)} Migrationsskript(e) ausführen<br>"
            f"{'&nbsp;&nbsp;3. Installer starten und Anwendung beenden<br>' if manifest.installer_file else ''}"
            "<br><b>Nutzerdaten werden nicht gelöscht.</b><br><br>"
            "Möchten Sie fortfahren?"
        )
        confirm.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        confirm.setDefaultButton(QMessageBox.StandardButton.Cancel)
        confirm.button(QMessageBox.StandardButton.Yes).setText("Ja, Update starten")
        confirm.button(QMessageBox.StandardButton.Cancel).setText("Abbrechen")

        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return

        user = Session.get_user() or {}
        user_id = user.get("id")

        self._btn_apply.setEnabled(False)
        self._btn_validate.setEnabled(False)

        progress = QProgressDialog("Update wird eingespielt...", None, 0, 0, self)
        progress.setWindowTitle("Update")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        self._worker = _UpdateWorker(self.update_service, self._selected_package, user_id)
        self._worker.finished.connect(lambda ok, msg, bp: self._on_update_done(ok, msg, bp, progress))
        self._worker.start()

    def _on_update_done(self, success: bool, message: str, backup_path: str, progress):
        progress.close()
        self._btn_validate.setEnabled(True)

        if success:
            QMessageBox.information(self, "Update erfolgreich", message)
            self._refresh_status()
            self._load_history_table()
            self._load_backup_table()
        else:
            QMessageBox.critical(self, "Update fehlgeschlagen", message)
            self._btn_apply.setEnabled(self._validated_manifest is not None)

    # ── Tab 1: Online-Update ───────────────────────────────────────────────

    def _build_online_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        url = self.update_service.get_manifest_url()
        if not url:
            warn = QLabel(
                "Kein Update-Server konfiguriert.\n"
                "Administration → Einstellungen → UPDATE_MANIFEST_URL setzen."
            )
            warn.setWordWrap(True)
            warn.setStyleSheet("color: #c0392b; font-size: 12px; padding: 4px;")
            layout.addWidget(warn)

        # Versions-Status-Karte
        status_frame = QFrame()
        status_frame.setObjectName("Card")
        grid = QGridLayout(status_frame)
        grid.setContentsMargins(16, 12, 16, 12)
        grid.setSpacing(8)
        grid.setColumnMinimumWidth(0, 160)

        for row, label in enumerate(("Installierte Version:", "Server-Version:", "Status:")):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #888; font-size: 12px;")
            grid.addWidget(lbl, row, 0)

        self._lbl_installed_ver = QLabel(APP_VERSION)
        self._lbl_installed_ver.setStyleSheet("font-weight: bold; font-size: 13px;")
        grid.addWidget(self._lbl_installed_ver, 0, 1)

        self._lbl_server_ver = QLabel("–")
        self._lbl_server_ver.setStyleSheet("font-size: 13px;")
        grid.addWidget(self._lbl_server_ver, 1, 1)

        self._lbl_update_status = QLabel("Noch nicht geprüft")
        self._lbl_update_status.setStyleSheet("font-size: 13px; color: #888;")
        grid.addWidget(self._lbl_update_status, 2, 1)

        layout.addWidget(status_frame)

        # Changelog
        group_cl = QGroupBox("Changelog")
        cl_layout = QVBoxLayout(group_cl)
        self._txt_online_changelog = QTextEdit()
        self._txt_online_changelog.setReadOnly(True)
        self._txt_online_changelog.setMaximumHeight(160)
        self._txt_online_changelog.setPlaceholderText(
            "Nach der Prüfung wird der Changelog hier angezeigt."
        )
        cl_layout.addWidget(self._txt_online_changelog)
        layout.addWidget(group_cl)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()

        self._btn_check_online = QPushButton("Auf Updates prüfen")
        self._btn_check_online.setObjectName("SoftButton")
        self._btn_check_online.setEnabled(bool(url))
        self._btn_check_online.clicked.connect(self._on_check_online)
        btn_row.addWidget(self._btn_check_online)

        btn_row.addStretch()

        self._btn_install_online = QPushButton("Jetzt installieren")
        self._btn_install_online.setEnabled(False)
        self._btn_install_online.setMinimumWidth(180)
        self._btn_install_online.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; font-weight: bold;"
            "  padding: 8px 20px; border-radius: 4px; font-size: 13px; }"
            "QPushButton:hover { background-color: #219a52; }"
            "QPushButton:disabled { background-color: #bbb; color: #888; }"
        )
        self._btn_install_online.clicked.connect(self._on_install_online)
        btn_row.addWidget(self._btn_install_online)

        layout.addLayout(btn_row)
        return w

    def _on_check_online(self):
        self._btn_check_online.setEnabled(False)
        self._btn_check_online.setText("Prüfe...")
        self._btn_install_online.setEnabled(False)
        self._online_check_result = None
        self._lbl_server_ver.setText("–")
        self._lbl_update_status.setText("Verbinde...")
        self._lbl_update_status.setStyleSheet("font-size: 13px; color: #888;")
        self._txt_online_changelog.clear()

        self._check_worker = _OnlineCheckWorker(self.update_service)
        self._check_worker.done.connect(self._on_check_done)
        self._check_worker.start()

    def _on_check_done(self, result) -> None:
        self._btn_check_online.setEnabled(True)
        self._btn_check_online.setText("Auf Updates prüfen")

        if result.error:
            self._lbl_update_status.setText(f"Fehler: {result.error}")
            self._lbl_update_status.setStyleSheet("font-size: 13px; color: #c0392b;")
            return

        if result.available:
            self._online_check_result = result
            self._lbl_server_ver.setText(result.version)
            self._lbl_update_status.setText("Update verfügbar")
            self._lbl_update_status.setStyleSheet(
                "font-size: 13px; color: #27ae60; font-weight: bold;"
            )
            self._txt_online_changelog.setPlainText(result.release_notes or "Kein Changelog vorhanden.")
            # Installer-Button nur aktivieren wenn auch ein direkter Link vorhanden ist
            self._btn_install_online.setEnabled(bool(result.installer_url))
            if not result.installer_url:
                self._lbl_update_status.setText(
                    "Update verfügbar — kein installer_url im Manifest (manuelles Update nötig)"
                )
        else:
            self._lbl_server_ver.setText(result.version or APP_VERSION)
            self._lbl_update_status.setText("Aktuell — kein Update verfügbar")
            self._lbl_update_status.setStyleSheet("font-size: 13px; color: #27ae60;")

    def _on_install_online(self):
        result = self._online_check_result
        if not result or not result.installer_url:
            return

        confirm = QMessageBox(self)
        confirm.setWindowTitle("Update installieren")
        confirm.setIcon(QMessageBox.Icon.Question)
        confirm.setText(
            f"<b>Update auf Version {result.version} installieren?</b><br><br>"
            "Ablauf:<br>"
            "&nbsp;&nbsp;1. Automatisches Datenbank-Backup<br>"
            "&nbsp;&nbsp;2. Installer herunterladen<br>"
            "&nbsp;&nbsp;3. Installer starten → Anwendung wird beendet<br><br>"
            "<b>Nutzerdaten werden nicht gelöscht.</b><br><br>"
            "Fortfahren?"
        )
        confirm.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        confirm.setDefaultButton(QMessageBox.StandardButton.Cancel)
        confirm.button(QMessageBox.StandardButton.Yes).setText("Ja, installieren")
        confirm.button(QMessageBox.StandardButton.Cancel).setText("Abbrechen")

        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return

        user_id = (Session.get_user() or {}).get("id")

        self._btn_install_online.setEnabled(False)
        self._btn_check_online.setEnabled(False)

        progress = QProgressDialog("Verbinde mit Update-Server...", None, 0, 100, self)
        progress.setWindowTitle("Update wird heruntergeladen")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()

        self._download_worker = _DownloadInstallWorker(
            update_service=self.update_service,
            installer_url=result.installer_url,
            version=result.version,
            changelog=result.release_notes or "",
            user_id=user_id,
        )
        self._download_worker.progress.connect(
            lambda done, total: self._on_download_progress(done, total, progress)
        )
        self._download_worker.error.connect(
            lambda msg: self._on_download_error(msg, progress)
        )
        self._download_worker.start()

    def _on_download_progress(self, done: int, total: int, progress: QProgressDialog) -> None:
        mb_done = done / 1024 / 1024
        if total > 0:
            pct = int(done / total * 100)
            mb_total = total / 1024 / 1024
            progress.setMaximum(100)
            progress.setValue(pct)
            progress.setLabelText(
                f"Herunterladen... {mb_done:.1f} / {mb_total:.1f} MB  ({pct} %)"
            )
        else:
            progress.setMaximum(0)  # Pulse-Modus
            progress.setLabelText(f"Herunterladen... {mb_done:.1f} MB")

    def _on_download_error(self, message: str, progress: QProgressDialog) -> None:
        progress.close()
        self._btn_check_online.setEnabled(True)
        self._btn_install_online.setEnabled(bool(self._online_check_result))
        QMessageBox.critical(self, "Update fehlgeschlagen", message)

    # ── Tab 3: Update-Verlauf ──────────────────────────────────────────────

    def _build_history_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        btn_refresh = QPushButton("Aktualisieren")
        btn_refresh.setObjectName("SoftButton")
        btn_refresh.clicked.connect(self._load_history_table)
        layout.addWidget(btn_refresh, alignment=Qt.AlignmentFlag.AlignRight)

        self._tbl_history = QTableWidget()
        self._tbl_history.setColumnCount(6)
        self._tbl_history.setHorizontalHeaderLabels([
            "Zeitpunkt", "Version", "Status", "Migrationen", "Backup", "Fehlermeldung"
        ])
        self._tbl_history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._tbl_history.horizontalHeader().setStretchLastSection(True)
        self._tbl_history.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl_history.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl_history.setAlternatingRowColors(True)
        layout.addWidget(self._tbl_history, 1)

        self._load_history_table()
        return w

    def _load_history_table(self):
        history = self.update_service.get_update_history()
        self._tbl_history.setRowCount(len(history))
        for row, entry in enumerate(history):
            status_icon = "Erfolgreich" if entry.get("status") == "SUCCESS" else "Fehlgeschlagen"
            migrations_raw = entry.get("applied_migrations") or "[]"
            try:
                import json
                migrations_list = json.loads(migrations_raw)
                migrations_text = str(len(migrations_list))
            except Exception:
                migrations_text = migrations_raw

            values = [
                (entry.get("applied_at", "")[:19]).replace("T", " "),
                entry.get("version", ""),
                status_icon,
                migrations_text,
                Path(entry.get("backup_path", "")).name if entry.get("backup_path") else "–",
                entry.get("error_message") or "",
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if col == 2:
                    item.setForeground(
                        Qt.GlobalColor.darkGreen
                        if entry.get("status") == "SUCCESS"
                        else Qt.GlobalColor.red
                    )
                self._tbl_history.setItem(row, col, item)

    # ── Tab 4: Backup-Verwaltung ───────────────────────────────────────────

    def _build_backup_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        info = QLabel(
            "Backups werden automatisch vor jedem Update erstellt. "
            "Sie können hier auch manuell ein Backup anlegen oder einen früheren "
            "Zustand wiederherstellen.\n"
            "ACHTUNG: Eine Wiederherstellung überschreibt die aktuelle Datenbank. "
            "Die Anwendung muss danach neu gestartet werden."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #555; font-size: 12px;")
        layout.addWidget(info)

        btn_row = QHBoxLayout()
        btn_create = QPushButton("Manuelles Backup erstellen")
        btn_create.setObjectName("SoftButton")
        btn_create.clicked.connect(self._on_create_backup)

        self._btn_restore = QPushButton("Ausgewähltes Backup wiederherstellen")
        self._btn_restore.setStyleSheet(
            "QPushButton { background-color: #e67e22; color: white; "
            "padding: 6px 14px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #d35400; }"
            "QPushButton:disabled { background-color: #bbb; color: #888; }"
        )
        self._btn_restore.setEnabled(False)
        self._btn_restore.clicked.connect(self._on_restore_backup)

        btn_refresh_b = QPushButton("Aktualisieren")
        btn_refresh_b.setObjectName("SoftButton")
        btn_refresh_b.clicked.connect(self._load_backup_table)

        btn_row.addWidget(btn_create)
        btn_row.addWidget(self._btn_restore)
        btn_row.addStretch()
        btn_row.addWidget(btn_refresh_b)
        layout.addLayout(btn_row)

        self._tbl_backups = QTableWidget()
        self._tbl_backups.setColumnCount(3)
        self._tbl_backups.setHorizontalHeaderLabels(["Dateiname", "Erstellt am", "Größe (KB)"])
        self._tbl_backups.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._tbl_backups.horizontalHeader().setStretchLastSection(False)
        self._tbl_backups.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tbl_backups.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl_backups.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl_backups.setAlternatingRowColors(True)
        self._tbl_backups.selectionModel().selectionChanged.connect(self._on_backup_selection)
        layout.addWidget(self._tbl_backups, 1)

        self._load_backup_table()
        return w

    def _load_backup_table(self):
        backups = self.update_service.list_backups()
        self._tbl_backups.setRowCount(len(backups))
        self._tbl_backups.setProperty("_backups", backups)
        for row, b in enumerate(backups):
            self._tbl_backups.setItem(row, 0, QTableWidgetItem(b["name"]))
            self._tbl_backups.setItem(row, 1, QTableWidgetItem(b["created"]))
            item_size = QTableWidgetItem(str(b["size_kb"]))
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._tbl_backups.setItem(row, 2, item_size)

        if hasattr(self, "_lbl_backup_count"):
            self._lbl_backup_count.setText(str(len(backups)))

    def _on_backup_selection(self):
        has_selection = bool(self._tbl_backups.selectedItems())
        self._btn_restore.setEnabled(has_selection)

    def _on_create_backup(self):
        worker = _BackupWorker(self.update_service)
        worker.finished.connect(self._on_backup_done)
        worker.start()
        self._backup_worker = worker  # keep reference

    def _on_backup_done(self, success: bool, message: str):
        if success:
            QMessageBox.information(self, "Backup erstellt", message)
            self._load_backup_table()
        else:
            QMessageBox.critical(self, "Backup fehlgeschlagen", message)

    def _on_restore_backup(self):
        rows = self._tbl_backups.selectedItems()
        if not rows:
            return
        selected_row = self._tbl_backups.currentRow()
        backups = self.update_service.list_backups()
        if selected_row >= len(backups):
            return
        backup_info = backups[selected_row]
        backup_path = Path(backup_info["path"])

        confirm = QMessageBox(self)
        confirm.setWindowTitle("Backup wiederherstellen – ACHTUNG")
        confirm.setIcon(QMessageBox.Icon.Critical)
        confirm.setText(
            f"<b>Datenbank aus Backup wiederherstellen?</b><br><br>"
            f"Backup: <b>{backup_info['name']}</b><br>"
            f"Erstellt: {backup_info['created']}<br><br>"
            f"<b style='color:red;'>WARNUNG:</b> Die aktuelle Datenbank wird durch den "
            f"Backup-Stand ersetzt.<br>"
            f"Alle seit diesem Backup eingetragenen Daten gehen verloren.<br><br>"
            f"Vor der Wiederherstellung wird ein automatisches Sicherheits-Backup erstellt.<br><br>"
            f"Die Anwendung muss danach neu gestartet werden.<br><br>"
            f"Sind Sie absolut sicher?"
        )
        confirm.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        confirm.setDefaultButton(QMessageBox.StandardButton.Cancel)
        confirm.button(QMessageBox.StandardButton.Yes).setText("Ja, jetzt wiederherstellen")

        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return

        success, message = self.update_service.restore_backup(backup_path)
        if success:
            QMessageBox.information(
                self, "Wiederherstellung erfolgreich",
                message + "\n\nBitte starten Sie die Anwendung jetzt neu.",
            )
        else:
            QMessageBox.critical(self, "Wiederherstellung fehlgeschlagen", message)
