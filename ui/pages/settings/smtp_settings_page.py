"""SMTP-Einstellungsseite — eigenständige Admin-Seite für Mailkonfiguration.

Ermöglicht:
- SMTP-Konfiguration laden, bearbeiten, speichern
- Verbindungstest mit Testmail
- Aktivierung/Deaktivierung
- Anzeige von Konfigurationsstatus und Testergebnis
"""
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QSpinBox, QGroupBox, QFormLayout,
    QFrame, QMessageBox, QScrollArea,
)
from ui.components.page_header import PageHeader
from services.settings_service import SettingsService


class _TestMailWorker(QThread):
    """Sendet Testmail im Hintergrund-Thread."""
    finished = pyqtSignal(bool, str)

    def __init__(self, config: dict, to_email: str):
        super().__init__()
        self._config = config
        self._to = to_email

    def run(self):
        try:
            from services.mail_service import MailService
            svc = MailService()
            ok, msg = svc.test_connection()
            if not ok:
                self.finished.emit(False, msg)
                return
            svc.send_html_mail(
                to_email=self._to,
                subject="SMTP-Testmail – Tischlein Deck Dich Vorarlberg",
                html_body=(
                    "<p>Diese E-Mail bestätigt, dass Ihre SMTP-Konfiguration korrekt eingerichtet ist.</p>"
                    "<p>Verein Tischlein Deck Dich Vorarlberg<br>Ladritschweg 10c · 6773 Vandans</p>"
                ),
            )
            self.finished.emit(True, f"Testmail erfolgreich an {self._to} gesendet.")
        except Exception as exc:
            self.finished.emit(False, str(exc))


class SmtpSettingsPage(QWidget):
    """Eigenständige, bearbeitbare SMTP-Konfigurationsseite."""

    def __init__(self, settings_service: SettingsService | None = None):
        super().__init__()
        self._svc = settings_service or SettingsService()
        self._worker: _TestMailWorker | None = None
        self._setup_ui()
        self._load_config()

    # ── UI-Aufbau ─────────────────────────────────────────────────────────────
    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        layout.addWidget(PageHeader(
            title="SMTP-Einstellungen",
            subtitle="Mailserver-Konfiguration für den automatischen E-Mail-Versand von Bescheiden, "
                     "Benachrichtigungen und Systeminfos.",
        ))

        # ── Status-Banner ─────────────────────────────────────────────────────
        self._status_banner = QLabel("")
        self._status_banner.setWordWrap(True)
        self._status_banner.setVisible(False)
        layout.addWidget(self._status_banner)

        # ── Konfiguration ─────────────────────────────────────────────────────
        cfg_box = QGroupBox("Mailserver-Konfiguration")
        cfg_form = QFormLayout(cfg_box)
        cfg_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        cfg_form.setHorizontalSpacing(24)
        cfg_form.setVerticalSpacing(12)

        self._active_cb = QCheckBox("SMTP-Mailversand aktiviert")
        self._active_cb.setToolTip(
            "Wenn deaktiviert, werden keine Mails versendet – Konfiguration bleibt erhalten."
        )
        cfg_form.addRow("", self._active_cb)

        self._host = QLineEdit()
        self._host.setPlaceholderText("z. B. smtp.office365.com oder mail.example.at")
        cfg_form.addRow("SMTP-Host *", self._host)

        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(587)
        self._port.setToolTip("587 = STARTTLS (empfohlen) · 465 = SSL/TLS · 25 = unverschlüsselt")
        cfg_form.addRow("Port *", self._port)

        self._user = QLineEdit()
        self._user.setPlaceholderText("Benutzername oder E-Mail-Adresse")
        cfg_form.addRow("Benutzername", self._user)

        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("Passwort / App-Secret")
        cfg_form.addRow("Passwort", self._password)

        self._show_pw = QCheckBox("Passwort anzeigen")
        self._show_pw.stateChanged.connect(
            lambda s: self._password.setEchoMode(
                QLineEdit.EchoMode.Normal if s else QLineEdit.EchoMode.Password
            )
        )
        cfg_form.addRow("", self._show_pw)

        self._tls = QCheckBox("STARTTLS verwenden (empfohlen für Port 587)")
        self._tls.setChecked(True)
        cfg_form.addRow("Verschlüsselung", self._tls)

        self._from_email = QLineEdit()
        self._from_email.setPlaceholderText("absender@example.at")
        cfg_form.addRow("Absender-E-Mail *", self._from_email)

        self._from_name = QLineEdit()
        self._from_name.setPlaceholderText("Verein Tischlein Deck Dich Vorarlberg")
        cfg_form.addRow("Absender-Name", self._from_name)

        layout.addWidget(cfg_box)

        # ── Testmail ──────────────────────────────────────────────────────────
        test_box = QGroupBox("Verbindungstest")
        test_layout = QVBoxLayout(test_box)
        test_layout.setSpacing(10)

        test_row = QHBoxLayout()
        test_row.addWidget(QLabel("Test-E-Mail an:"))
        self._test_email = QLineEdit()
        self._test_email.setPlaceholderText("test@example.at")
        self._test_email.setMinimumWidth(260)
        test_row.addWidget(self._test_email, 1)

        self._test_btn = QPushButton("Testmail senden")
        self._test_btn.setObjectName("SoftButton")
        self._test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._test_btn.clicked.connect(self._send_test_mail)
        test_row.addWidget(self._test_btn)

        self._conn_btn = QPushButton("Verbindung prüfen")
        self._conn_btn.setObjectName("SoftButton")
        self._conn_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._conn_btn.clicked.connect(self._check_connection)
        test_row.addWidget(self._conn_btn)

        test_layout.addLayout(test_row)

        self._test_result = QLabel("")
        self._test_result.setWordWrap(True)
        self._test_result.setVisible(False)
        test_layout.addWidget(self._test_result)

        layout.addWidget(test_box)

        # ── Hinweise ──────────────────────────────────────────────────────────
        hint_box = QGroupBox("Hinweise")
        hint_layout = QVBoxLayout(hint_box)
        hint = QLabel(
            "<b>Microsoft 365 / Outlook:</b> smtp.office365.com · Port 587 · STARTTLS<br>"
            "<b>Gmail (App-Passwort):</b> smtp.gmail.com · Port 587 · STARTTLS<br>"
            "<b>Eigenem Server:</b> Host/Port laut Ihrem Provider<br><br>"
            "<b>Sicherheit:</b> Das Passwort wird verschlüsselt in der lokalen Datenbank gespeichert. "
            "Verwenden Sie nach Möglichkeit App-Spezifische Passwörter statt des Hauptpassworts."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 12px; color: #555;")
        hint_layout.addWidget(hint)
        layout.addWidget(hint_box)

        # ── Aktions-Buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._reset_btn = QPushButton("Zurücksetzen")
        self._reset_btn.setObjectName("SoftButton")
        self._reset_btn.setToolTip("Gespeicherte Konfiguration neu laden")
        self._reset_btn.clicked.connect(self._load_config)
        btn_row.addWidget(self._reset_btn)

        self._save_btn = QPushButton("Konfiguration speichern")
        self._save_btn.setObjectName("PrimaryButton")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(self._save_btn)

        layout.addLayout(btn_row)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── Konfiguration laden/speichern ─────────────────────────────────────────
    def _load_config(self) -> None:
        cfg = self._svc.get_smtp_config()
        self._active_cb.setChecked(bool(cfg.get("SMTP_ACTIVE", False)))
        self._host.setText(str(cfg.get("SMTP_HOST") or ""))
        port_val = cfg.get("SMTP_PORT", 587)
        try:
            self._port.setValue(int(port_val) if port_val else 587)
        except (ValueError, TypeError):
            self._port.setValue(587)
        self._user.setText(str(cfg.get("SMTP_USER") or ""))
        self._password.setText(str(cfg.get("SMTP_PASSWORD") or ""))
        self._tls.setChecked(bool(cfg.get("SMTP_USE_TLS", True)))
        self._from_email.setText(str(cfg.get("SMTP_FROM_EMAIL") or ""))
        self._from_name.setText(str(cfg.get("SMTP_FROM_NAME") or "Verein Tischlein Deck Dich Vorarlberg"))
        self._show_status("Konfiguration geladen.", success=True)

    def _save_config(self) -> None:
        host = self._host.text().strip()
        from_email = self._from_email.text().strip()
        if self._active_cb.isChecked():
            if not host:
                QMessageBox.warning(self, "Pflichtfeld fehlt", "SMTP-Host ist erforderlich wenn Mailversand aktiv ist.")
                return
            if not from_email:
                QMessageBox.warning(self, "Pflichtfeld fehlt", "Absender-E-Mail ist erforderlich.")
                return

        config = {
            "SMTP_ACTIVE":     self._active_cb.isChecked(),
            "SMTP_HOST":       host,
            "SMTP_PORT":       self._port.value(),
            "SMTP_USER":       self._user.text().strip(),
            "SMTP_PASSWORD":   self._password.text(),
            "SMTP_USE_TLS":    self._tls.isChecked(),
            "SMTP_FROM_EMAIL": from_email,
            "SMTP_FROM_NAME":  self._from_name.text().strip() or "Verein Tischlein Deck Dich Vorarlberg",
        }
        try:
            self._svc.save_smtp_config(config)
            self._show_status("Konfiguration erfolgreich gespeichert.", success=True)
        except PermissionError as exc:
            QMessageBox.warning(self, "Keine Berechtigung", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"Konfiguration konnte nicht gespeichert werden:\n{exc}")

    # ── Verbindungstest ───────────────────────────────────────────────────────
    def _check_connection(self) -> None:
        self._set_test_running(True)
        try:
            from services.mail_service import MailService
            ok, msg = MailService().test_connection()
            self._show_test_result(ok, msg)
        except Exception as exc:
            self._show_test_result(False, str(exc))
        finally:
            self._set_test_running(False)

    def _send_test_mail(self) -> None:
        to = self._test_email.text().strip()
        if not to:
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Test-E-Mail-Adresse eingeben.")
            return

        # Zuerst speichern
        self._save_config()

        self._set_test_running(True)
        self._worker = _TestMailWorker(config={}, to_email=to)
        self._worker.finished.connect(self._on_test_finished)
        self._worker.start()

    def _on_test_finished(self, success: bool, message: str) -> None:
        self._set_test_running(False)
        self._show_test_result(success, message)

    def _set_test_running(self, running: bool) -> None:
        self._test_btn.setEnabled(not running)
        self._conn_btn.setEnabled(not running)
        self._test_btn.setText("Wird gesendet …" if running else "Testmail senden")

    def _show_test_result(self, success: bool, message: str) -> None:
        bg  = "#e8f8ed" if success else "#fdeaea"
        fg  = "#1a5c37" if success else "#b42318"
        bdr = "#b7e4cf" if success else "#f5c2c0"
        self._test_result.setStyleSheet(
            f"background:{bg}; color:{fg}; border:1px solid {bdr}; "
            "border-radius:6px; padding:8px 12px; font-size:12px;"
        )
        icon = "✓" if success else "✗"
        self._test_result.setText(f"{icon} {message}")
        self._test_result.setVisible(True)

    def _show_status(self, message: str, success: bool = True) -> None:
        bg  = "#e8f8ed" if success else "#fdeaea"
        fg  = "#1a5c37" if success else "#b42318"
        bdr = "#b7e4cf" if success else "#f5c2c0"
        self._status_banner.setStyleSheet(
            f"background:{bg}; color:{fg}; border:1px solid {bdr}; "
            "border-radius:6px; padding:8px 12px; font-size:12px;"
        )
        self._status_banner.setText(message)
        self._status_banner.setVisible(True)
