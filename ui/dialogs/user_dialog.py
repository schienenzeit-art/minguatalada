from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QCheckBox,
)


class AddUserDialog(QDialog):
    def __init__(self, roles: list[dict], locations: list[dict], user: dict | None = None):
        super().__init__()
        self.roles = roles
        self.locations = locations
        self.user = user
        self.user_data = None
        self.setup_ui()

    def setup_ui(self):
        title = "Neuen Benutzer anlegen" if self.user is None else "Benutzer bearbeiten"
        self.setWindowTitle(title)
        self.setMinimumWidth(360)

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.full_name_input = QLineEdit()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.role_combo = QComboBox()
        self.role_combo.addItem("Bitte Rolle wählen", None)
        for role in self.roles:
            self.role_combo.addItem(role["name"], role["id"])

        self.location_combo = QComboBox()
        self.location_combo.addItem("Kein Standort", None)
        for location in self.locations:
            self.location_combo.addItem(location["name"], location["id"])

        self.active_checkbox = QCheckBox("Aktiv")
        self.active_checkbox.setChecked(True)

        if self.user is not None:
            self.full_name_input.setText(self.user.get("full_name", ""))
            self.username_input.setText(self.user.get("username", ""))
            self.active_checkbox.setChecked(bool(self.user.get("is_active", True)))

            role_id = self.user.get("role_id")
            if role_id is not None:
                role_index = self.role_combo.findData(role_id)
                if role_index >= 0:
                    self.role_combo.setCurrentIndex(role_index)

            location_id = self.user.get("location_id")
            if location_id is not None:
                location_index = self.location_combo.findData(location_id)
                if location_index >= 0:
                    self.location_combo.setCurrentIndex(location_index)

        form_layout.addRow(QLabel("Vollständiger Name"), self.full_name_input)
        form_layout.addRow(QLabel("Benutzername"), self.username_input)
        form_layout.addRow(QLabel("Passwort"), self.password_input)
        form_layout.addRow(QLabel("Rolle"), self.role_combo)
        form_layout.addRow(QLabel("Standort"), self.location_combo)
        form_layout.addRow(self.active_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def accept(self) -> None:
        full_name = self.full_name_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        role_id = self.role_combo.currentData()

        if not full_name or not username or role_id is None:
            QMessageBox.warning(
                self,
                "Ungültige Eingabe",
                "Bitte füllen Sie Name, Benutzername und Rolle aus.",
            )
            return

        if self.user is None and not password:
            QMessageBox.warning(
                self,
                "Ungültige Eingabe",
                "Bitte geben Sie ein Passwort ein.",
            )
            return

        location_id = self.location_combo.currentData()
        self.user_data = {
            "full_name": full_name,
            "username": username,
            "password": password if password else None,
            "role_id": role_id,
            "location_id": location_id,
            "is_active": bool(self.active_checkbox.isChecked()),
        }
        super().accept()

    def get_user_data(self) -> dict:
        return self.user_data
