from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFormLayout, QLineEdit,
    QFrame, QScrollArea, QMessageBox,
)

from core.session import Session
from services.settings_service import SettingsService
from ui.components.page_header import PageHeader


class SystemSettingsPage(QWidget):
    """Systemparameter: Fallnummernpräfix, Update-Server-URL, Systeminfo."""

    def __init__(self, settings_service: SettingsService | None = None):
        super().__init__()
        self._svc = settings_service or SettingsService()
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        layout.addWidget(PageHeader(
            title="Systemparameter",
            subtitle="Applikationsweite Konfiguration: Fallnummernpräfix und Systemeinstellungen.",
        ))

        is_admin = Session.is_admin()

        if not is_admin:
            banner = QLabel(
                "Ansichtsmodus — nur Administratoren dürfen diese Werte ändern."
            )
            banner.setStyleSheet(
                "background: #fff8e1; color: #7a5c00; border: 1px solid #ffe082; "
                "border-radius: 6px; padding: 8px 14px; font-size: 12px;"
            )
            layout.addWidget(banner)

        # ── Fallnummernkonfiguration ──────────────────────────────────────────
        grp_case = QGroupBox("Fallnummernkonfiguration")
        form_case = QFormLayout(grp_case)
        form_case.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_case.setHorizontalSpacing(32)
        form_case.setVerticalSpacing(14)

        self._prefix = QLineEdit()
        self._prefix.setPlaceholderText("z. B. AS")
        self._prefix.setMaxLength(10)
        self._prefix.setMaximumWidth(140)
        self._prefix.setEnabled(is_admin)
        form_case.addRow("Fallnummernpräfix:", self._prefix)
        form_case.addRow(
            "",
            self._hint(
                "Präfix für alle neu erzeugten Fallnummern.\n"
                "Beispiel: 'AS' → AS-2026-000001"
            ),
        )

        self._lbl_example_case = QLabel()
        self._lbl_example_case.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 12px; color: #555;"
        )
        form_case.addRow("Vorschau:", self._lbl_example_case)

        self._prefix.textChanged.connect(self._update_case_preview)
        layout.addWidget(grp_case)

        # ── Update-Server ─────────────────────────────────────────────────────
        grp_update = QGroupBox("Update-Server")
        form_update = QFormLayout(grp_update)
        form_update.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_update.setHorizontalSpacing(32)
        form_update.setVerticalSpacing(14)

        self._manifest_url = QLineEdit()
        self._manifest_url.setPlaceholderText("https://updates.example.at/manifest.json")
        self._manifest_url.setMinimumWidth(380)
        self._manifest_url.setEnabled(is_admin)
        form_update.addRow("Manifest-URL:", self._manifest_url)
        form_update.addRow(
            "",
            self._hint(
                "URL zum JSON-Manifest für automatische Update-Prüfung.\n"
                "Leer lassen wenn kein externer Update-Server vorhanden ist.\n"
                "Die vollständige Update-Verwaltung befindet sich unter: "
                "Administration → Software-Update-Center."
            ),
        )

        layout.addWidget(grp_update)

        # ── Systeminformationen (nur Anzeige) ─────────────────────────────────
        grp_info = QGroupBox("Systeminformationen")
        form_info = QFormLayout(grp_info)
        form_info.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_info.setHorizontalSpacing(32)
        form_info.setVerticalSpacing(10)

        from services.update_service import APP_VERSION
        form_info.addRow("Anwendungsversion:", QLabel(APP_VERSION))
        form_info.addRow("Datenbank:",          QLabel("SQLite"))
        form_info.addRow("Angemeldeter Benutzer:",
                         QLabel(Session.get_full_name() or "–"))
        form_info.addRow("Rolle:",              QLabel(Session.get_role_name() or "–"))

        layout.addWidget(grp_info)
        layout.addStretch()

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_reset = QPushButton("Zurücksetzen")
        btn_reset.setObjectName("SoftButton")
        btn_reset.clicked.connect(self._load)

        btn_save = QPushButton("Speichern")
        btn_save.setObjectName("PrimaryButton")
        btn_save.setEnabled(is_admin)
        btn_save.clicked.connect(self._save)

        btn_row.addWidget(btn_reset)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── Hilfsmethoden ─────────────────────────────────────────────────────────

    @staticmethod
    def _hint(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 11px; color: #888;")
        return lbl

    def _update_case_preview(self) -> None:
        prefix = self._prefix.text().strip() or "AS"
        from datetime import datetime
        year = datetime.now().year
        self._lbl_example_case.setText(f"{prefix}-{year}-000001")

    # ── Daten laden / speichern ───────────────────────────────────────────────

    def _load(self) -> None:
        self._prefix.setText(str(self._svc.get("CASE_NUMBER_PREFIX", "AS")))
        self._manifest_url.setText(str(self._svc.get("UPDATE_MANIFEST_URL", "") or ""))
        self._update_case_preview()

    def _save(self) -> None:
        if not Session.is_admin():
            QMessageBox.warning(
                self, "Keine Berechtigung",
                "Nur Administratoren dürfen Systemparameter ändern."
            )
            return

        values = {
            "CASE_NUMBER_PREFIX":  self._prefix.text().strip() or "AS",
            "UPDATE_MANIFEST_URL": self._manifest_url.text().strip(),
        }

        changed: list[str] = []
        for key, new_val in values.items():
            current = str(self._svc.get(key, "") or "")
            if current != new_val:
                try:
                    self._svc.update_setting(key, new_val)
                    changed.append(key)
                except Exception as e:
                    QMessageBox.critical(
                        self, "Fehler",
                        f"Einstellung '{key}' konnte nicht gespeichert werden:\n{e}"
                    )
                    return

        if not changed:
            QMessageBox.information(self, "Keine Änderungen", "Es wurden keine Werte geändert.")
        else:
            QMessageBox.information(
                self, "Gespeichert",
                f"Gespeichert: {', '.join(changed)}"
            )
        self._load()
