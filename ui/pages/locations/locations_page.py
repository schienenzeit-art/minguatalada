from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidgetItem, QHeaderView, QScrollArea, QInputDialog, QMessageBox
from ui.components.table_widget import TableWidget

from services.location_service import LocationService
from services.user_service import UserService
from ui.components.page_header import PageHeader
from ui.components.action_button import ActionButton


class LocationsPage(QWidget):
    def __init__(self, location_service: LocationService | None = None, user_service: UserService | None = None):
        super().__init__()
        self.location_service = location_service or LocationService()
        self.user_service = user_service or UserService()
        self.setup_ui()
        self.load_locations()

    def setup_ui(self):
        self.setObjectName("locationsPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = PageHeader(
            title="Standorte",
            subtitle="Übersicht über Standorte, Adressen und Mitarbeiterverteilung.",
            action_text="Standort hinzufügen",
            action_callback=self.open_add_location_dialog,
        )
        layout.addWidget(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Standort suchen")
        self.search_input.setMinimumWidth(320)
        self.search_input.returnPressed.connect(self.load_locations)
        self.refresh_button = ActionButton("Aktualisieren")
        self.refresh_button.clicked.connect(self.load_locations)
        self.toggle_active_button = ActionButton("Status umschalten")
        self.toggle_active_button.clicked.connect(self.toggle_location_active)
        toolbar.addWidget(self.search_input)
        toolbar.addWidget(self.refresh_button)
        toolbar.addWidget(self.toggle_active_button)
        layout.addLayout(toolbar)

        self.table = TableWidget(2)
        self.table.setHorizontalHeaderLabels(["Standort", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.setObjectName("dataTable")
        self.table.cellDoubleClicked.connect(self.on_location_row_double_clicked)

        content_box = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.table)
        content_box.setLayout(content_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content_box)
        layout.addWidget(scroll)

        self.setLayout(layout)

    def load_locations(self) -> None:
        search_text = self.search_input.text().strip().lower()
        locations = self.location_service.list_locations(include_inactive=True)

        self.table.setRowCount(0)
        for location in locations:
            if search_text and search_text not in (location.get("name", "").lower()):
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(location.get("name", "-")))
            status_text = "Aktiv" if location.get("is_active") else "Inaktiv"
            self.table.setItem(row, 1, QTableWidgetItem(status_text))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, location.get("id"))

    def open_add_location_dialog(self) -> None:
        name, ok = QInputDialog.getText(self, "Neuen Standort anlegen", "Name des Standorts:")
        if not ok or not name.strip():
            return

        result = self.location_service.create_location(name.strip())
        if result:
            QMessageBox.information(self, "Erfolg", "Standort wurde erfolgreich angelegt.")
            self.load_locations()
        else:
            QMessageBox.warning(self, "Fehler", "Standort konnte nicht angelegt werden.")

    def on_location_row_double_clicked(self, row: int, column: int) -> None:
        item = self.table.item(row, 0)
        if item is None:
            return

        location_id = item.data(Qt.ItemDataRole.UserRole)
        if not location_id:
            return

        current_name = item.text()
        new_name, ok = QInputDialog.getText(self, "Standort bearbeiten", "Name des Standorts:", text=current_name)
        if not ok or not new_name.strip():
            return

        updated = self.location_service.update_location(location_id, new_name.strip())
        if updated:
            QMessageBox.information(self, "Erfolg", "Standort wurde aktualisiert.")
            self.load_locations()
        else:
            QMessageBox.warning(self, "Fehler", "Standort konnte nicht aktualisiert werden.")

    def toggle_location_active(self) -> None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Auswahl fehlt", "Bitte wählen Sie einen Standort aus.")
            return

        row = selected_items[0].row()
        location_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not location_id:
            return

        current_status = self.table.item(row, 1).text()
        is_active = current_status != "Aktiv"
        updated = self.location_service.set_location_active(location_id, is_active)
        if updated:
            QMessageBox.information(self, "Erfolg", "Standortstatus wurde aktualisiert.")
            self.load_locations()
        else:
            QMessageBox.warning(self, "Fehler", "Standortstatus konnte nicht geändert werden.")
