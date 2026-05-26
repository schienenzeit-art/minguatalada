from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
)

from ui.components.page_header import PageHeader
from ui.components.table_widget import TableWidget
from ui.pages.person_dossier_dialog import PersonDossierDialog
from services.person_service import PersonService
from services.location_service import LocationService
from core.claim_status import ClaimStatus


class PersonDossierPage(QWidget):
    def __init__(
        self,
        person_service: PersonService | None = None,
        location_service: LocationService | None = None,
        navigate_callback=None,
    ):
        super().__init__()
        self.person_service = person_service or PersonService()
        self.location_service = location_service or LocationService()
        self.navigate_callback = navigate_callback
        self.setup_ui()
        self.load_locations()
        self.load_persons()

    def setup_ui(self):
        self.setObjectName("personDossierPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = PageHeader(
            title="Personendossier",
            subtitle="Filtern Sie Personen nach Name, Standort und Status. Dossier per Doppelklick öffnen.",
        )
        layout.addWidget(header)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Name")
        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("Vorname")
        self.location_combo = QComboBox()
        self.location_combo.setMinimumWidth(180)
        self.status_combo = QComboBox()
        self.status_combo.setMinimumWidth(180)
        self.filter_button = QPushButton("Filter anwenden")
        self.filter_button.setObjectName("primaryButton")
        self.filter_button.clicked.connect(self.load_persons)

        filter_row.addWidget(self.last_name_input)
        filter_row.addWidget(self.first_name_input)
        filter_row.addWidget(self.location_combo)
        filter_row.addWidget(self.status_combo)
        filter_row.addWidget(self.filter_button)

        layout.addLayout(filter_row)

        self.table = TableWidget(6)
        self.table.setHorizontalHeaderLabels([
            "Name",
            "Vorname",
            "Kategorie",
            "Standort",
            "Status",
            "Fälle",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self.on_person_double_clicked)
        self.table.setObjectName("dataTable")

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
        self.location_combo.clear()
        self.location_combo.addItem("Alle Standorte", None)
        for location in self.location_service.list_active_locations():
            self.location_combo.addItem(location.get("name", "-"), location.get("id"))

        self.status_combo.clear()
        self.status_combo.addItem("Alle Status", None)
        self.status_combo.addItem("Kein Fall", "KEIN_FALL")
        for status in ClaimStatus.ALL_STATUSES:
            self.status_combo.addItem(ClaimStatus.get_display(status), status)

    def load_persons(self) -> None:
        last_name = self.last_name_input.text().strip() or None
        first_name = self.first_name_input.text().strip() or None
        location_id = self.location_combo.currentData()
        status = self.status_combo.currentData()

        persons = self.person_service.list_persons(
            last_name=last_name,
            first_name=first_name,
            location_id=location_id,
            status=status,
        )

        self.table.setRowCount(0)
        for person in persons:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(person.get("last_name") or "-"))
            self.table.setItem(row, 1, QTableWidgetItem(person.get("first_name") or "-"))
            self.table.setItem(row, 2, QTableWidgetItem(person.get("category_name") or "-"))
            self.table.setItem(row, 3, QTableWidgetItem(person.get("location_name") or "-"))
            self.table.setItem(
                row,
                4,
                QTableWidgetItem(
                    self._format_person_status(person.get("latest_claim_status")),
                ),
            )
            self.table.setItem(row, 5, QTableWidgetItem(str(person.get("claim_count", 0))))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, person.get("id"))

    def on_person_double_clicked(self, row: int, column: int) -> None:
        person_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not person_id:
            return

        dialog = PersonDossierDialog(person_id=person_id)
        dialog.exec()

    def apply_filters(
        self,
        person_id: int | None = None,
        last_name: str | None = None,
        first_name: str | None = None,
        location_id: int | None = None,
        status: str | None = None,
    ) -> None:
        if last_name is not None:
            self.last_name_input.setText(last_name)
        if first_name is not None:
            self.first_name_input.setText(first_name)
        if location_id is not None:
            index = self.location_combo.findData(location_id)
            if index >= 0:
                self.location_combo.setCurrentIndex(index)
        if status is not None:
            index = self.status_combo.findData(status)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)

        self.load_persons()
        if person_id is not None:
            self._open_person_by_id(person_id)

    def _open_person_by_id(self, person_id: int) -> None:
        dialog = PersonDossierDialog(person_id=person_id)
        dialog.exec()

    def _format_person_status(self, status: str | None) -> str:
        if not status:
            return "Kein Fall"
        return ClaimStatus.get_display(status)
