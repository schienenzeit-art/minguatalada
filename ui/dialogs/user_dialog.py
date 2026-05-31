from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QCheckBox,
)

from core.constants import NON_LOGIN_ROLES


class AddUserDialog(QDialog):
    def __init__(self, roles: list[dict], locations: list[dict], user: dict | None = None):
        super().__init__()
        flags = self.windowFlags()
        flags |= Qt.WindowType.Window
        flags |= Qt.WindowType.WindowMinimizeButtonHint
        flags |= Qt.WindowType.WindowMaximizeButtonHint
        self.setWindowFlags(flags)
        self.roles = roles
        self.locations = locations
        self.user = user
        self.user_data = None
        self.setup_ui()

    def setup_ui(self):
        title = "Neuen Benutzer anlegen" if self.user is None else "Benutzer bearbeiten"
        self.setWindowTitle(title)
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self._form = QFormLayout()
        self._form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self._form.setHorizontalSpacing(24)
        self._form.setVerticalSpacing(10)

        # ── Felder ────────────────────────────────────────────────────────────
        self.full_name_input = QLineEdit()
        self._form.addRow("Vollständiger Name *", self.full_name_input)

        self.username_input = QLineEdit()
        self._form.addRow("Benutzername *", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._form.addRow("Passwort *", self.password_input)

        self.role_combo = QComboBox()
        self.role_combo.addItem("Bitte Rolle wählen", None)
        for role in self.roles:
            self.role_combo.addItem(role["name"], role["id"])
        self._form.addRow("Rolle *", self.role_combo)

        self.location_combo = QComboBox()
        self.location_combo.addItem("Kein Standort", None)
        for location in self.locations:
            self.location_combo.addItem(location["name"], location["id"])
        self._form.addRow("Standort", self.location_combo)

        self.active_checkbox = QCheckBox("Aktiv")
        self.active_checkbox.setChecked(True)
        self._form.addRow("", self.active_checkbox)

        layout.addLayout(self._form)

        # ── Info-Banner für Freiwillige (initial versteckt) ───────────────────
        self._volunteer_info = QLabel(
            "Freiwillige erhalten keinen Systemzugang und benötigen kein Passwort.\n"
            "Der Datensatz dient ausschliesslich der Verwaltung und Kartenzuordnung."
        )
        self._volunteer_info.setWordWrap(True)
        self._volunteer_info.setStyleSheet(
            "background: #fff8e1; color: #7a5c00; border: 1px solid #ffe082; "
            "border-radius: 6px; padding: 10px 14px; font-size: 12px;"
        )
        self._volunteer_info.setVisible(False)
        layout.addWidget(self._volunteer_info)

        # ── Buttons ────���──────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # ── Bestehenden Benutzer laden ───────────────────────────────────────��
        if self.user is not None:
            self.full_name_input.setText(self.user.get("full_name", ""))
            self.username_input.setText(self.user.get("username", ""))
            self.active_checkbox.setChecked(bool(self.user.get("is_active", True)))

            role_id = self.user.get("role_id")
            if role_id is not None:
                idx = self.role_combo.findData(role_id)
                if idx >= 0:
                    self.role_combo.setCurrentIndex(idx)

            location_id = self.user.get("location_id")
            if location_id is not None:
                idx = self.location_combo.findData(location_id)
                if idx >= 0:
                    self.location_combo.setCurrentIndex(idx)

        # Rolle-Änderungs-Handler verbinden + initialen Zustand setzen
        self.role_combo.currentIndexChanged.connect(self._on_role_changed)
        self._on_role_changed()

    # ── Rolle-Wechsel ────────��────────────────────────────────────────────────

    def _is_volunteer_selected(self) -> bool:
        return self.role_combo.currentText() in NON_LOGIN_ROLES

    def _on_role_changed(self) -> None:
        is_volunteer = self._is_volunteer_selected()
        # Passwort-Zeile ein-/ausblenden (QFormLayout.setRowVisible – Qt 5.12+)
        try:
            self._form.setRowVisible(self.password_input, not is_volunteer)
        except AttributeError:
            # Fallback für ältere Qt-Versionen
            self.password_input.setVisible(not is_volunteer)
        self._volunteer_info.setVisible(is_volunteer)

    # ── Validierung & Speichern ──��────────────────────────────────────────────

    def accept(self) -> None:
        full_name = self.full_name_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        role_id = self.role_combo.currentData()
        is_volunteer = self._is_volunteer_selected()

        if not full_name or not username or role_id is None:
            QMessageBox.warning(
                self,
                "Ungültige Eingabe",
                "Bitte füllen Sie Name, Benutzername und Rolle aus.",
            )
            return

        # Passwort ist nur für reguläre Benutzer (nicht Freiwillige) Pflicht
        if not is_volunteer and self.user is None and not password:
            QMessageBox.warning(
                self,
                "Passwort erforderlich",
                "Bitte vergeben Sie ein Passwort für diesen Benutzer.",
            )
            return

        location_id = self.location_combo.currentData()
        self.user_data = {
            "full_name":    full_name,
            "username":     username,
            "password":     password if not is_volunteer else "",
            "role_id":      role_id,
            "location_id":  location_id,
            "is_active":    bool(self.active_checkbox.isChecked()),
            "is_volunteer": is_volunteer,
        }
        super().accept()

    def get_user_data(self) -> dict:
        return self.user_data
