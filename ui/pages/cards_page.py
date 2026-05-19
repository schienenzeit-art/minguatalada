from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QLineEdit,
    QGroupBox,
    QFormLayout,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from services.card_service import CardService
from services.claim_service import ClaimService
from services.location_service import LocationService
from ui.pages.claim_detail_page import ClaimDetailPage
from core.card_status import CardStatus


class CardsPage(QWidget):
    """
    Kartenverwaltungs-Seite.
    Zeigt alle Karten in einer Tabelle mit Filterung.
    """

    def __init__(
        self,
        card_service: CardService | None = None,
        location_service: LocationService | None = None,
        claim_service: ClaimService | None = None,
    ):
        super().__init__()
        self.card_service = card_service or CardService()
        self.location_service = location_service or LocationService()
        self.claim_service = claim_service or ClaimService()
        self.cards = []
        self.setup_ui()
        self.load_cards()

    def setup_ui(self):
        """Baut die UI auf."""
        layout = QVBoxLayout()

        # Titel
        title_label = QLabel("Kartenverwaltung")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)

        # Filter-Bereich
        filter_group = QGroupBox("Filter")
        filter_layout = QFormLayout()

        self.location_combo = QComboBox()
        self.location_combo.addItem("Alle Standorte", None)
        locations = self.location_service.list_active_locations()
        for loc in locations:
            self.location_combo.addItem(loc["name"], loc["id"])
        self.location_combo.currentIndexChanged.connect(self.on_filter_changed)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Alle Status", None)
        for status in self.card_service.get_all_card_statuses():
            display_name = self.card_service.get_card_status_display(status)
            self.status_combo.addItem(display_name, status)
        self.status_combo.currentIndexChanged.connect(self.on_filter_changed)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Suche: Kartennummer, Name...")
        self.search_input.textChanged.connect(self.on_filter_changed)

        filter_layout.addRow("Standort:", self.location_combo)
        filter_layout.addRow("Status:", self.status_combo)
        filter_layout.addRow("Suche:", self.search_input)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Buttons-Bereich
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        refresh_btn = QPushButton("Aktualisieren")
        refresh_btn.clicked.connect(self.load_cards)
        buttons_layout.addWidget(refresh_btn)

        layout.addLayout(buttons_layout)

        # Tabelle
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Kartennummer",
            "Person",
            "Fallnummer",
            "Standort",
            "Ausgestellt",
            "Ablauf",
            "Status",
        ])
        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 110)
        self.table.setColumnWidth(5, 110)
        self.table.setColumnWidth(6, 120)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemDoubleClicked.connect(self.on_card_double_clicked)

        layout.addWidget(self.table)

        # Hinweis
        info_label = QLabel()
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        self.info_label = info_label
        layout.addWidget(info_label)

        self.setLayout(layout)

    def load_cards(self):
        """Lädt die Kartenliste neu."""
        self.on_filter_changed()

    def on_filter_changed(self):
        """Wird aufgerufen wenn Filter sich ändern."""
        location_id = self.location_combo.currentData()
        status = self.status_combo.currentData()
        search_text = self.search_input.text().strip() or None

        self.cards = self.card_service.list_cards(
            location_id=location_id,
            status=status,
            search_text=search_text,
        )

        self.render_table()

    def render_table(self):
        """Rendert die Kartentabelle."""
        self.table.setRowCount(len(self.cards))

        for row_idx, card in enumerate(self.cards):
            card_number = card.get("card_number", "-")
            person_name = self._format_person_name(card)
            case_number = card.get("case_number", "-")
            location = card.get("location_name", "-")
            issue_date = card.get("issue_date", "-")
            expiry_date = card.get("expiry_date", "-")
            status = card.get("status", "-")

            self.table.setItem(row_idx, 0, QTableWidgetItem(card_number))
            self.table.setItem(row_idx, 1, QTableWidgetItem(person_name))
            self.table.setItem(row_idx, 2, QTableWidgetItem(case_number))
            self.table.setItem(row_idx, 3, QTableWidgetItem(location))
            self.table.setItem(row_idx, 4, QTableWidgetItem(issue_date))
            self.table.setItem(row_idx, 5, QTableWidgetItem(expiry_date))

            # Status mit farblicher Hervorhebung
            status_display = self.card_service.get_card_status_display(status)
            status_item = QTableWidgetItem(status_display)
            status_item.setData(Qt.ItemDataRole.UserRole, status)

            # Status-Farben
            if status == CardStatus.AKTIV:
                status_item.setBackground(QColor("#d4edda"))  # grün
            elif status == CardStatus.BALD_ABLAUFEND:
                status_item.setBackground(QColor("#fff3cd"))  # gelb
            elif status == CardStatus.ABGELAUFEN:
                status_item.setBackground(QColor("#f8d7da"))  # rot
            elif status == CardStatus.GESPERRT:
                status_item.setBackground(QColor("#e2e3e5"))  # grau
            elif status == CardStatus.ARCHIVIERT:
                status_item.setBackground(QColor("#d1ecf1"))  # blau

            self.table.setItem(row_idx, 6, status_item)

        # Info-Text aktualisieren
        count = len(self.cards)
        self.info_label.setText(f"Insgesamt: {count} Karten")

    def on_card_double_clicked(self, item):
        """Wird aufgerufen bei Doppelklick auf eine Karte."""
        row = item.row()
        if 0 <= row < len(self.cards):
            card = self.cards[row]
            claim_id = card.get("claim_id")
            if claim_id:
                dialog = ClaimDetailPage(
                    claim_id=claim_id,
                    claim_service=self.claim_service,
                    card_service=self.card_service,
                )
                dialog.exec()
            else:
                QMessageBox.information(
                    self,
                    "Karte ausgewählt",
                    f"Kartennummer: {card.get('card_number', '-')}",
                )

    def apply_filters(
        self,
        status: str | None = None,
        location_id: int | None = None,
        search_text: str | None = None,
    ) -> None:
        self.location_combo.blockSignals(True)
        self.status_combo.blockSignals(True)

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

        if search_text is not None:
            self.search_input.setText(search_text)

        self.location_combo.blockSignals(False)
        self.status_combo.blockSignals(False)

        self.on_filter_changed()

    @staticmethod
    def _format_person_name(card: dict) -> str:
        """Formatiert den Namen der Person."""
        first = card.get("person_first_name", "")
        last = card.get("person_last_name", "")
        if first and last:
            return f"{first} {last}"
        elif last:
            return last
        elif first:
            return first
        return "-"
