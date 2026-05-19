from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QInputDialog,
)

from services.role_service import RoleService


class RoleManagementPage(QWidget):
    def __init__(self, role_service: RoleService | None = None):
        super().__init__()
        self.role_service = role_service or RoleService()
        self.setup_ui()
        self.load_roles()

    def setup_ui(self):
        layout = QVBoxLayout()
        header_label = QLabel("Rollenverwaltung")
        header_label.setStyleSheet("font-size: 20px; font-weight: bold;")

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Neue Rolle")
        self.edit_button = QPushButton("Rolle bearbeiten")
        self.toggle_button = QPushButton("Aktiv/Inaktiv schalten")
        self.refresh_button = QPushButton("Aktualisieren")

        self.add_button.clicked.connect(self.on_add_role)
        self.edit_button.clicked.connect(self.on_edit_role)
        self.toggle_button.clicked.connect(self.on_toggle_active)
        self.refresh_button.clicked.connect(self.load_roles)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.toggle_button)
        button_layout.addWidget(self.refresh_button)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Aktiv"])
        self.table.hideColumn(0)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(header_label)
        layout.addLayout(button_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_roles(self):
        roles = self.role_service.list_roles(include_inactive=True)
        self.table.setRowCount(0)
        for role in roles:
            row = self.table.rowCount()
            self.table.insertRow(row)
            id_item = QTableWidgetItem(str(role["id"]))
            id_item.setData(Qt.ItemDataRole.UserRole, role["id"])
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, QTableWidgetItem(role["name"]))
            self.table.setItem(row, 2, QTableWidgetItem("Ja" if role["is_active"] else "Nein"))

    def on_add_role(self):
        name, ok = QInputDialog.getText(self, "Neue Rolle", "Rollenname:")
        if not ok or not name.strip():
            return

        self.role_service.create_role(name.strip())
        self.load_roles()

    def on_edit_role(self):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Auswahl fehlt", "Bitte wählen Sie eine Rolle aus.")
            return

        id_item = self.table.item(selected_row, 0)
        if id_item is None:
            return

        role_id = int(id_item.data(Qt.ItemDataRole.UserRole))
        current_name = self.table.item(selected_row, 1).text()
        name, ok = QInputDialog.getText(self, "Rolle bearbeiten", "Rollenname:", text=current_name)
        if not ok or not name.strip():
            return

        self.role_service.update_role(role_id, name.strip())
        self.load_roles()

    def on_toggle_active(self):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Auswahl fehlt", "Bitte wählen Sie eine Rolle aus.")
            return

        id_item = self.table.item(selected_row, 0)
        active_item = self.table.item(selected_row, 2)
        if id_item is None or active_item is None:
            return

        role_id = int(id_item.data(Qt.ItemDataRole.UserRole))
        is_active = active_item.text() == "Ja"
        self.role_service.set_role_active(role_id, not is_active)
        self.load_roles()
