"""Dialog zum Anlegen von Personal / Freiwilligen."""
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QVBoxLayout, QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt

from services.user_service import UserService
from services.role_service import RoleService
from services.location_service import LocationService


class StaffFormDialog(QDialog):
    MODE_DEFAULT_ROLES = {
        "management": "Standortleitung",
        "staff":      "Mitarbeiter",
        "volunteers": "Mitarbeiter",
    }

    def __init__(self, mode: str = "staff", user_service: UserService | None = None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.user_service = user_service or UserService()
        self.role_service = RoleService()
        self.location_service = LocationService()
        self.setWindowTitle("Personal erfassen")
        self.setMinimumWidth(420)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setHorizontalSpacing(20)
        form.setVerticalSpacing(10)

        self.full_name = QLineEdit()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Mindestens 8 Zeichen")

        self.role_combo = QComboBox()
        for role in self.role_service.list_roles():
            self.role_combo.addItem(role["name"], role["id"])
        # Vorauswahl je nach Modus
        default_role = self.MODE_DEFAULT_ROLES.get(self.mode, "Mitarbeiter")
        idx = self.role_combo.findText(default_role)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)

        self.location_combo = QComboBox()
        for loc in self.location_service.list_locations():
            self.location_combo.addItem(loc["name"], loc["id"])

        form.addRow("Name", self.full_name)
        form.addRow("Benutzername", self.username)
        form.addRow("Passwort", self.password)
        form.addRow("Rolle", self.role_combo)
        form.addRow("Standort", self.location_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def on_save(self):
        full_name = self.full_name.text().strip()
        username = self.username.text().strip()
        password = self.password.text()
        role_id = self.role_combo.currentData()
        location_id = self.location_combo.currentData()

        if not full_name:
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Name eingeben.")
            return
        if not username:
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Benutzername eingeben.")
            return
        if len(password) < 8:
            QMessageBox.warning(self, "Passwort", "Passwort muss mindestens 8 Zeichen haben.")
            return

        try:
            self.user_service.create_user(
                full_name=full_name,
                username=username,
                password=password,
                role_id=role_id,
                location_id=location_id,
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Konnte nicht gespeichert werden: {e}")
