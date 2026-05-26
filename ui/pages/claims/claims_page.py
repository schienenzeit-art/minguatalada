from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidgetItem, QHeaderView, QScrollArea, QMessageBox
from ui.components.table_widget import TableWidget

from core.claim_status import ClaimStatus
from services.card_service import CardService
from services.case_service import CaseService
from services.claim_service import ClaimService
from ui.components.page_header import PageHeader
from ui.components.action_button import ActionButton
from ui.pages.case_create_page import CaseCreateDialog
from ui.pages.claim_detail_page import ClaimDetailPage


class ClaimsPage(QWidget):
    def __init__(
        self,
        claim_service: ClaimService | None = None,
        case_service: CaseService | None = None,
        card_service: CardService | None = None,
    ):
        super().__init__()
        self.claim_service = claim_service or ClaimService()
        self.case_service = case_service or CaseService()
        self.card_service = card_service or CardService()
        self.active_filters = {}  # KPI-Filter speichern
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("claimsPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = PageHeader(
            title="Anträge",
            subtitle="Verwalten Sie Ihre Fälle und eröffnen Sie neue Anträge direkt aus der modernen Oberfläche.",
            action_text="Neuen Antrag anlegen",
            action_callback=self.open_create_dialog,
        )
        layout.addWidget(header)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Suchen nach Nummer, Name oder Status")
        self.search_input.setMinimumWidth(320)
        self.search_input.returnPressed.connect(self.load_claims)
        self.filter_button = ActionButton("Aktualisieren")
        self.filter_button.clicked.connect(self.load_claims)
        filter_row.addWidget(self.search_input)
        filter_row.addWidget(self.filter_button)

        layout.addLayout(filter_row)

        self.table = TableWidget(6)
        self.table.setHorizontalHeaderLabels(["Antragsnummer", "Person", "Status", "Standort", "Bearbeiter", "Datum"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.setObjectName("dataTable")
        self.table.cellDoubleClicked.connect(self.on_claim_row_activated)

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
        self.load_claims()

    def load_claims(self) -> None:
        search_text = self.search_input.text().strip() or None
        status_filter = self.active_filters.get("status")
        statuses_filter = self.active_filters.get("statuses")
        claims = self.claim_service.list_claims(
            search_text=search_text,
            status=status_filter,
            statuses=statuses_filter,
        )

        self.table.setRowCount(0)
        if not claims:
            self.table.insertRow(0)
            self.table.setItem(0, 0, QTableWidgetItem("Keine Anträge gefunden."))
            self.table.setSpan(0, 0, 1, self.table.columnCount())
            return

        for claim in claims:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(claim.get("case_number", "-")))
            self.table.setItem(row, 1, QTableWidgetItem(claim.get("person_display_name", "-")))
            self.table.setItem(row, 2, QTableWidgetItem(ClaimStatus.get_display(claim.get("status", "-"))))
            self.table.setItem(row, 3, QTableWidgetItem(claim.get("location_name", "-")))
            self.table.setItem(row, 4, QTableWidgetItem(claim.get("examiner_name", "-")))
            self.table.setItem(row, 5, QTableWidgetItem(claim.get("created_at", "-")))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, claim.get("id"))

    def open_create_dialog(self) -> None:
        dialog = CaseCreateDialog(
            self,
            case_service=self.case_service,
            claim_service=self.claim_service,
        )
        dialog.exec()
        self.load_claims()

    def set_filters(self, filters: dict | None = None) -> None:
        if filters:
            self.active_filters = filters
        self.load_claims()

    def apply_filters(self, status: str | None = None, statuses: list | None = None, **kwargs) -> None:
        self.active_filters = {"status": status, "statuses": statuses}
        self.load_claims()

    def on_claim_row_activated(self, row: int, column: int) -> None:
        item = self.table.item(row, 0)
        if item is None:
            return
        claim_id = item.data(Qt.ItemDataRole.UserRole)
        if not claim_id:
            return

        dialog = ClaimDetailPage(
            claim_id=claim_id,
            claim_service=self.claim_service,
            card_service=self.card_service,
        )
        dialog.exec()
        self.load_claims()
