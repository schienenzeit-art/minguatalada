from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTableWidgetItem,
    QHeaderView,
)
from ui.components.table_widget import TableWidget

from core.session import Session
from services.report_service import ReportService
from ui.components.page_header import PageHeader


class ReportsPage(QWidget):
    def __init__(self, report_service: ReportService | None = None):
        super().__init__()
        self.report_service = report_service or ReportService()
        self.setup_ui()
        self.load_reports()

    def setup_ui(self):
        self.setObjectName("reportsPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = PageHeader(
            title="Berichte",
            subtitle="Auswertungen und Statusberichte nach Standort.",
            action_text="Aktualisieren",
            action_callback=self.load_reports,
        )
        layout.addWidget(header)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)
        filter_row.addWidget(QLabel("Standort:"))

        self.location_combo = QComboBox()
        self.location_combo.setMinimumWidth(260)
        self.location_combo.currentIndexChanged.connect(self.load_reports)
        filter_row.addWidget(self.location_combo)

        self.refresh_button = QPushButton("Aktualisieren")
        self.refresh_button.clicked.connect(self.load_reports)
        filter_row.addWidget(self.refresh_button)
        filter_row.addStretch()

        layout.addLayout(filter_row)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        self.total_claims_label = QLabel("Anträge: 0")
        self.total_cards_label = QLabel("Karten: 0")
        self.total_claims_label.setObjectName("reportStat")
        self.total_cards_label.setObjectName("reportStat")

        stats_row.addWidget(self.total_claims_label)
        stats_row.addWidget(self.total_cards_label)
        stats_row.addStretch()
        layout.addLayout(stats_row)

        self.claim_table = TableWidget(2)
        self.claim_table.setHorizontalHeaderLabels(["Anspruchsstatus", "Anzahl"])
        self.claim_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.claim_table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.claim_table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)

        self.card_table = TableWidget(2)
        self.card_table.setHorizontalHeaderLabels(["Kartenstatus", "Anzahl"])
        self.card_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.card_table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.card_table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(QLabel("Anspruchsübersicht nach Status"))
        layout.addWidget(self.claim_table)
        layout.addWidget(QLabel("Kartenübersicht nach Status"))
        layout.addWidget(self.card_table)
        layout.addStretch()

        self.setLayout(layout)

    def load_reports(self):
        self.location_combo.blockSignals(True)
        self.location_combo.clear()
        self.location_combo.addItem("Alle Standorte", None)
        locations = self.report_service.get_locations(include_inactive=True)
        for location in locations:
            self.location_combo.addItem(location["name"], location["id"])

        if not Session.is_admin():
            location_id = Session.get_location_id()
            for index in range(self.location_combo.count()):
                if self.location_combo.itemData(index) == location_id:
                    self.location_combo.setCurrentIndex(index)
                    break
            self.location_combo.setEnabled(False)

        self.location_combo.blockSignals(False)
        selected_location = self.location_combo.currentData()

        report = self.report_service.get_location_report(selected_location)
        self.total_claims_label.setText(f"Anträge: {report['total_claims']}")
        self.total_cards_label.setText(f"Karten: {report['total_cards']}")

        self.claim_table.setRowCount(0)
        for item in report["claim_status_counts"]:
            row = self.claim_table.rowCount()
            self.claim_table.insertRow(row)
            self.claim_table.setItem(row, 0, QTableWidgetItem(item["status"]))
            self.claim_table.setItem(row, 1, QTableWidgetItem(str(item["count"])))

        self.card_table.setRowCount(0)
        for item in report["card_status_counts"]:
            row = self.card_table.rowCount()
            self.card_table.insertRow(row)
            self.card_table.setItem(row, 0, QTableWidgetItem(item["status"]))
            self.card_table.setItem(row, 1, QTableWidgetItem(str(item["count"])))

