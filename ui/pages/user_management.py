from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QHeaderView,
)

from services.user_service import UserService
from ui.dialogs.user_dialog import AddUserDialog


class UserManagementPage(QWidget):
    def __init__(self, user_service: UserService | None = None):
        super().__init__()
        self.user_service = user_service or UserService()
        self.setup_ui()
        self.load_users()

    def setup_ui(self):
        layout = QVBoxLayout()
        header_label = QLabel("Benutzerverwaltung")
        header_label.setStyleSheet("font-size: 20px; font-weight: bold;")

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Neuen Benutzer")
        self.edit_button = QPushButton("Benutzer bearbeiten")
        self.refresh_button = QPushButton("Aktualisieren")
        self.toggle_active_button = QPushButton("Aktiv/Inaktiv schalten")

        self.add_button.clicked.connect(self.on_add_user)
        self.edit_button.clicked.connect(self.on_edit_user)
        self.refresh_button.clicked.connect(self.load_users)
        self.toggle_active_button.clicked.connect(self.on_toggle_active)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.toggle_active_button)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Name",
            "Benutzername",
            "Rolle",
            "Standort",
            "Aktiv",
        ])
        self.table.hideColumn(0)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(header_label)
        layout.addLayout(button_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_users(self):
        users = self.user_service.get_all_users()
        self.table.setRowCount(0)

        for user in users:
            row = self.table.rowCount()
            self.table.insertRow(row)

            id_item = QTableWidgetItem(str(user["id"]))
            id_item.setData(Qt.ItemDataRole.UserRole, user["id"])
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, QTableWidgetItem(user["full_name"]))
            self.table.setItem(row, 2, QTableWidgetItem(user["username"]))
            self.table.setItem(row, 3, QTableWidgetItem(user["role_name"] or "-"))
            self.table.setItem(row, 4, QTableWidgetItem(user["location_name"] or "-"))
            self.table.setItem(row, 5, QTableWidgetItem("Ja" if user["is_active"] else "Nein"))

    def on_add_user(self):
        roles = self.user_service.get_roles()
        locations = self.user_service.get_locations()
        dialog = AddUserDialog(roles, locations)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        user_data = dialog.get_user_data()
        result = self.user_service.create_user(
            user_data["full_name"],
            user_data["username"],
            user_data["password"],
            user_data["role_id"],
            user_data["location_id"],
            user_data["is_active"],
        )

        if not result["success"]:
            QMessageBox.warning(self, "Fehler", result["message"])
            return

        QMessageBox.information(self, "Erfolg", result["message"])
        self.load_users()

    def on_edit_user(self):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Auswahl fehlt", "Bitte wählen Sie einen Benutzer aus.")
            return

        id_item = self.table.item(selected_row, 0)
        if id_item is None:
            return

        user_id = int(id_item.data(Qt.ItemDataRole.UserRole))
        user = self.user_service.get_user_by_id(user_id)
        if user is None:
            QMessageBox.warning(self, "Fehler", "Benutzer nicht gefunden.")
            return

        roles = self.user_service.get_roles()
        locations = self.user_service.get_locations()
        dialog = AddUserDialog(roles, locations, user=user)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        user_data = dialog.get_user_data()
        result = self.user_service.update_user(
            user_id=user_id,
            full_name=user_data["full_name"],
            username=user_data["username"],
            role_id=user_data["role_id"],
            location_id=user_data["location_id"],
            is_active=user_data["is_active"],
            password=user_data["password"],
        )

        if not result["success"]:
            QMessageBox.warning(self, "Fehler", result["message"])
            return

        QMessageBox.information(self, "Erfolg", result["message"])
        self.load_users()

    def on_toggle_active(self):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Auswahl fehlt", "Bitte wählen Sie einen Benutzer aus.")
            return

        id_item = self.table.item(selected_row, 0)
        active_item = self.table.item(selected_row, 5)
        if id_item is None or active_item is None:
            return

        user_id = int(id_item.data(Qt.ItemDataRole.UserRole))
        is_active = active_item.text() == "Ja"
        self.user_service.set_user_active(user_id, not is_active)
        self.load_users()
