from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QTableWidgetItem,
    QHeaderView,
    QInputDialog,
    QMessageBox,
)
from ui.components.table_widget import TableWidget

from core.session import Session
from services.location_service import LocationService
from services.user_service import UserService


class LocationPage(QWidget):
    def __init__(
        self,
        user_service: UserService | None = None,
        location_service: LocationService | None = None,
    ):
        super().__init__()
        self.user_service = user_service or UserService()
        self.location_service = location_service or LocationService()
        self.locations = []
        self.setup_ui()
        self.load_locations()
        self.refresh_users()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)

        title_label = QLabel("Standortbereich")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("font-size: 14px; color: #555555;")

        control_layout = QHBoxLayout()
        self.location_select = QComboBox()
        self.refresh_button = QPushButton("Aktualisieren")
        self.refresh_button.clicked.connect(self.refresh_users)

        control_layout.addWidget(QLabel("Standort wählen:"))
        control_layout.addWidget(self.location_select)
        control_layout.addWidget(self.refresh_button)

        self.table = TableWidget(5)
        self.table.setHorizontalHeaderLabels([
            "Name",
            "Benutzername",
            "Rolle",
            "Standort",
            "Aktiv",
        ])
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.location_table = TableWidget(3)
        self.location_table.setHorizontalHeaderLabels(["ID", "Standort", "Aktiv"])
        self.location_table.hideColumn(0)
        self.location_table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.location_table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.location_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.add_location_button = QPushButton("Neuen Standort")
        self.edit_location_button = QPushButton("Standort bearbeiten")
        self.toggle_location_button = QPushButton("Aktiv/Inaktiv schalten")

        self.add_location_button.clicked.connect(self.on_add_location)
        self.edit_location_button.clicked.connect(self.on_edit_location)
        self.toggle_location_button.clicked.connect(self.on_toggle_location)

        if not Session.is_admin():
            self.add_location_button.hide()
            self.edit_location_button.hide()
            self.toggle_location_button.hide()

        location_button_layout = QHBoxLayout()
        location_button_layout.addWidget(self.add_location_button)
        location_button_layout.addWidget(self.edit_location_button)
        location_button_layout.addWidget(self.toggle_location_button)

        layout.addWidget(title_label)
        layout.addWidget(self.info_label)
        layout.addLayout(control_layout)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Standorte"))
        layout.addLayout(location_button_layout)
        layout.addWidget(self.location_table)
        layout.addStretch()

        self.setLayout(layout)

    def load_locations(self):
        self.locations = self.user_service.get_locations()
        self.location_select.clear()
        if Session.is_admin():
            self.location_select.addItem("Alle Standorte", None)

        selected_name = Session.get_location_name()
        current_index = 0
        for index, location in enumerate(self.locations, start=0):
            self.location_select.addItem(location["name"], location["id"])
            if location["name"] == selected_name:
                current_index = index + (1 if Session.is_admin() else 0)

        self.location_select.setCurrentIndex(current_index)
        if not Session.is_admin():
            self.location_select.setEnabled(False)

        self.load_location_table()

    def load_location_table(self):
        locations = self.location_service.list_locations(include_inactive=True)
        self.location_table.setRowCount(0)
        for location in locations:
            row = self.location_table.rowCount()
            self.location_table.insertRow(row)
            id_item = QTableWidgetItem(str(location["id"]))
            id_item.setData(Qt.ItemDataRole.UserRole, location["id"])
            self.location_table.setItem(row, 0, id_item)
            self.location_table.setItem(row, 1, QTableWidgetItem(location["name"]))
            self.location_table.setItem(row, 2, QTableWidgetItem("Ja" if location["is_active"] else "Nein"))

    def on_add_location(self):
        name, ok = QInputDialog.getText(self, "Neuen Standort hinzufügen", "Standortname:")
        if not ok or not name.strip():
            return

        self.location_service.create_location(name.strip())
        self.load_locations()
        self.refresh_users()

    def on_edit_location(self):
        selected_row = self.location_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Auswahl fehlt", "Bitte wählen Sie einen Standort aus.")
            return

        id_item = self.location_table.item(selected_row, 0)
        if id_item is None:
            return

        location_id = int(id_item.data(Qt.ItemDataRole.UserRole))
        current_name = self.location_table.item(selected_row, 1).text()
        name, ok = QInputDialog.getText(self, "Standort bearbeiten", "Standortname:", text=current_name)
        if not ok or not name.strip():
            return

        self.location_service.update_location(location_id, name.strip())
        self.load_locations()
        self.refresh_users()

    def on_toggle_location(self):
        selected_row = self.location_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Auswahl fehlt", "Bitte wählen Sie einen Standort aus.")
            return

        id_item = self.location_table.item(selected_row, 0)
        active_item = self.location_table.item(selected_row, 2)
        if id_item is None or active_item is None:
            return

        location_id = int(id_item.data(Qt.ItemDataRole.UserRole))
        is_active = active_item.text() == "Ja"
        self.location_service.set_location_active(location_id, not is_active)
        self.load_locations()
        self.refresh_users()

    def refresh_users(self):
        selected_data = self.location_select.currentData()
        users = self.user_service.get_users_by_location(selected_data)

        self.info_label.setText(
            f"Angezeigte Daten für Standort: {self.location_select.currentText()}"
        )
        self.table.setRowCount(0)

        for user in users:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(user["full_name"]))
            self.table.setItem(row, 1, QTableWidgetItem(user["username"]))
            self.table.setItem(row, 2, QTableWidgetItem(user["role_name"] or "-"))
            self.table.setItem(row, 3, QTableWidgetItem(user["location_name"] or "-"))
            self.table.setItem(row, 4, QTableWidgetItem("Ja" if user["is_active"] else "Nein"))
