from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QDialogButtonBox,
    QMessageBox,
)

from services.user_service import UserService


class ForcePasswordDialog(QDialog):
    """Shown after login when must_change_password is set — user cannot skip."""

    def __init__(self, user_id: int, user_service: UserService | None = None):
        super().__init__()
        self.user_id = user_id
        self.user_service = user_service or UserService()
        self.setWindowTitle("Passwort ändern")
        self.setModal(True)
        self.setMinimumWidth(400)
        flags = self.windowFlags()
        flags &= ~Qt.WindowType.WindowCloseButtonHint
        self.setWindowFlags(flags)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        info = QLabel(
            "Ihr Passwort muss vor der weiteren Nutzung geändert werden.\n"
            "Das neue Passwort muss mindestens 10 Zeichen lang sein."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #334e68; font-size: 13px;")
        layout.addWidget(info)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)

        self.current_pw = QLineEdit()
        self.current_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_pw.setPlaceholderText("Aktuelles Passwort")

        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pw.setPlaceholderText("Neues Passwort (min. 10 Zeichen)")

        self.confirm_pw = QLineEdit()
        self.confirm_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pw.setPlaceholderText("Neues Passwort wiederholen")

        form.addRow("Aktuelles Passwort:", self.current_pw)
        form.addRow("Neues Passwort:", self.new_pw)
        form.addRow("Bestätigung:", self.confirm_pw)
        layout.addLayout(form)

        save_btn = QPushButton("Passwort speichern")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

    def _save(self):
        current = self.current_pw.text()
        new = self.new_pw.text()
        confirm = self.confirm_pw.text()

        if not current or not new or not confirm:
            QMessageBox.warning(self, "Fehlende Eingabe", "Bitte alle Felder ausfüllen.")
            return

        if new != confirm:
            QMessageBox.warning(self, "Passwörter stimmen nicht überein", "Das neue Passwort und die Bestätigung stimmen nicht überein.")
            return

        if len(new) < 10:
            QMessageBox.warning(self, "Passwort zu kurz", "Das neue Passwort muss mindestens 10 Zeichen lang sein.")
            return

        result = self.user_service.change_password(self.user_id, current, new)
        if not result.get("success"):
            QMessageBox.warning(self, "Fehler", result.get("message", "Passwort konnte nicht geändert werden."))
            return

        try:
            self.user_service.set_must_change_password(self.user_id, False)
        except Exception:
            pass

        QMessageBox.information(self, "Passwort geändert", "Ihr Passwort wurde erfolgreich geändert.")
        self.accept()

    def reject(self):
        QMessageBox.information(
            self,
            "Passwortänderung erforderlich",
            "Die Passwortänderung ist verpflichtend. Bitte geben Sie ein neues Passwort ein.",
        )
