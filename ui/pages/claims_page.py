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
    QLineEdit,
)
from ui.components.table_widget import TableWidget

from core.session import Session
from services.case_service import CaseService
from services.card_service import CardService
from services.category_service import CategoryService
from services.claim_service import ClaimService
from services.user_service import UserService
from ui.pages.claim_detail_page import ClaimDetailPage
from ui.pages.case_create_page import CaseCreateDialog
from ui.pages.person_dossier_dialog import PersonDossierDialog


class ClaimsPage(QWidget):
    def __init__(
        self,
        claim_service: ClaimService | None = None,
        case_service: CaseService | None = None,
        card_service: CardService | None = None,
        user_service: UserService | None = None,
        category_service: CategoryService | None = None,
    ):
        super().__init__()
        self.claim_service = claim_service or ClaimService()
        self.case_service = case_service or CaseService()
        self.card_service = card_service or CardService()
        self.user_service = user_service or UserService()
        self.category_service = category_service or CategoryService()
        self.claims = []
        self.setup_ui()
        self.load_filters()
        self.refresh_claims()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)

        title_label = QLabel("Fälle")
        title_label.setObjectName("SectionTitle")

        filter_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Suche nach Name oder Fallnummer")
        self.search_input.returnPressed.connect(self.refresh_claims)

        self.location_combo = QComboBox()
        self.status_combo = QComboBox()
        self.category_combo = QComboBox()
        self.examiner_combo = QComboBox()
        self.refresh_button = QPushButton("Aktualisieren")
        self.refresh_button.clicked.connect(self.refresh_claims)

        filter_layout.addWidget(QLabel("Suche:"))
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(QLabel("Standort:"))
        filter_layout.addWidget(self.location_combo)
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.status_combo)
        filter_layout.addWidget(QLabel("Kategorie:"))
        filter_layout.addWidget(self.category_combo)
        filter_layout.addWidget(QLabel("Prüfer:"))
        filter_layout.addWidget(self.examiner_combo)
        filter_layout.addWidget(self.refresh_button)
        self.create_button = QPushButton("Neuer Antrag")
        self.create_button.clicked.connect(self.open_create_dialog)
        filter_layout.addWidget(self.create_button)

        self.table = TableWidget(8)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Fallnummer",
            "Person",
            "Kategorie",
            "Standort",
            "Status",
            "Zeitraum",
            "Erstellt",
        ])
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.hideColumn(0)
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)

        layout.addWidget(title_label)
        layout.addLayout(filter_layout)
        layout.addWidget(self.table)
        layout.addStretch()
        self.setLayout(layout)

    def load_filters(self):
        locations = self.user_service.get_locations()
        self.location_combo.clear()
        self.location_combo.addItem("Alle Standorte", None)
        for location in locations:
            self.location_combo.addItem(location["name"], location["id"])

        if not Session.is_admin():
            location_id = Session.get_location_id()
            for index in range(self.location_combo.count()):
                if self.location_combo.itemData(index) == location_id:
                    self.location_combo.setCurrentIndex(index)
                    break
            self.location_combo.setEnabled(False)

        self.status_combo.clear()
        self.status_combo.addItem("Alle Status", None)
        for status in self.claim_service.get_claim_statuses():
            self.status_combo.addItem(status, status)
        self.status_combo.setCurrentIndex(0)

        self.category_combo.clear()
        self.category_combo.addItem("Alle Kategorien", None)
        for category in self.category_service.list_categories():
            self.category_combo.addItem(category["name"], category["id"])
        self.category_combo.setCurrentIndex(0)

        self.examiner_combo.clear()
        self.examiner_combo.addItem("Alle Prüfer", None)
        location_id = None if Session.is_admin() else Session.get_location_id()
        for user in self.user_service.get_users_by_location(location_id):
            self.examiner_combo.addItem(user["full_name"], user["id"])
        self.examiner_combo.setCurrentIndex(0)

        self.location_combo.currentIndexChanged.connect(self.on_filter_changed)
        self.status_combo.currentIndexChanged.connect(self.on_filter_changed)
        self.category_combo.currentIndexChanged.connect(self.on_filter_changed)
        self.examiner_combo.currentIndexChanged.connect(self.on_filter_changed)

    def refresh_claims(self):
        location_id = self.location_combo.currentData()
        status = self.status_combo.currentData()
        category_id = self.category_combo.currentData()
        examiner_id = self.examiner_combo.currentData()
        search_text = self.search_input.text().strip() or None

        self.claims = self.claim_service.list_claims(
            location_id=location_id,
            status=status,
            category_id=category_id,
            examiner_id=examiner_id,
            search_text=search_text,
        )

        self.table.setRowCount(0)
        for claim in self.claims:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(claim["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(claim.get("case_number") or "-"))
            self.table.setItem(row, 2, QTableWidgetItem(claim.get("person_display_name") or "-"))
            self.table.setItem(row, 3, QTableWidgetItem(claim.get("category_name") or "-"))
            self.table.setItem(row, 4, QTableWidgetItem(claim["location_name"] or "-"))
            self.table.setItem(row, 5, QTableWidgetItem(claim["status"] or "-"))
            self.table.setItem(
                row,
                6,
                QTableWidgetItem(
                    f"{claim['start_date'] or '-'} bis {claim['end_date'] or '-'}"
                ),
            )
            self.table.setItem(row, 7, QTableWidgetItem(claim["created_at"] or "-"))

    def on_table_double_clicked(self, row: int, column: int):
        id_item = self.table.item(row, 0)
        if id_item is None:
            return

        try:
            claim_id = int(id_item.text())
        except ValueError:
            return

        claim = self.claims[row]
        if column == 2 and claim.get("person_id"):
            dialog = PersonDossierDialog(person_id=claim["person_id"])
            dialog.exec()
            return

        dialog = ClaimDetailPage(
            claim_id=claim_id,
            claim_service=self.claim_service,
            card_service=self.card_service,
        )
        dialog.exec()

    def apply_filters(
        self,
        status: str | None = None,
        location_id: int | None = None,
        category_id: int | None = None,
        examiner_id: int | None = None,
        search_text: str | None = None,
    ) -> None:
        self.location_combo.blockSignals(True)
        self.status_combo.blockSignals(True)
        self.category_combo.blockSignals(True)
        self.examiner_combo.blockSignals(True)

        if status is not None:
            for index in range(self.status_combo.count()):
                if self.status_combo.itemData(index) == status:
                    self.status_combo.setCurrentIndex(index)
                    break

        if location_id is not None:
            for index in range(self.location_combo.count()):
                if self.location_combo.itemData(index) == location_id:
                    self.location_combo.setCurrentIndex(index)
                    break

        if category_id is not None:
            for index in range(self.category_combo.count()):
                if self.category_combo.itemData(index) == category_id:
                    self.category_combo.setCurrentIndex(index)
                    break

        if examiner_id is not None:
            for index in range(self.examiner_combo.count()):
                if self.examiner_combo.itemData(index) == examiner_id:
                    self.examiner_combo.setCurrentIndex(index)
                    break

        if search_text is not None:
            self.search_input.setText(search_text)

        self.location_combo.blockSignals(False)
        self.status_combo.blockSignals(False)
        self.category_combo.blockSignals(False)
        self.examiner_combo.blockSignals(False)

        self.refresh_claims()

    def on_filter_changed(self):
        self.refresh_claims()

    def open_create_dialog(self):
        dlg = CaseCreateDialog(
            self,
            case_service=self.case_service,
            claim_service=self.claim_service,
        )
        dlg.exec()
        # after possible creation refresh list
        self.refresh_claims()
