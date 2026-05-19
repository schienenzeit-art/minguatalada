from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QLabel

from services.dashboard_service import DashboardService
from ui.components.page_header import PageHeader
from ui.components.stat_card import StatCard


class DashboardPage(QWidget):
    def __init__(self, dashboard_service: DashboardService | None = None, navigate_callback=None):
        super().__init__()
        self.dashboard_service = dashboard_service or DashboardService()
        self.navigate_callback = navigate_callback
        self.kpi_cards: list[StatCard] = []
        self.summary_cards: list[StatCard] = []
        self.setup_ui()
        self.load_dashboard()

    def setup_ui(self):
        self.setObjectName("dashboardPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(22)

        header = PageHeader(
            title="Dashboard",
            subtitle="Operative Steuerung, aktuelle Systemkennzahlen und Arbeitsziele",
            action_text="Bericht exportieren",
        )
        layout.addWidget(header)

        self.stats_section = QWidget()
        self.stats_section.setObjectName("pageSection")
        self.stats_section_layout = QGridLayout()
        self.stats_section_layout.setContentsMargins(20, 20, 20, 20)
        self.stats_section_layout.setSpacing(16)
        self.stats_section.setLayout(self.stats_section_layout)
        layout.addWidget(self.stats_section)

        summary_title = QLabel("Schnelle Zusammenfassung")
        summary_title.setStyleSheet("font-size: 18px; font-weight: 600; margin-bottom: 8px;")
        layout.addWidget(summary_title)

        self.summary_section = QWidget()
        self.summary_section.setObjectName("pageSection")
        self.summary_layout = QHBoxLayout()
        self.summary_layout.setContentsMargins(20, 20, 20, 20)
        self.summary_layout.setSpacing(16)
        self.summary_section.setLayout(self.summary_layout)
        layout.addWidget(self.summary_section)

        content = QWidget()
        content.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        outer_layout = QVBoxLayout()
        outer_layout.addWidget(scroll)
        self.setLayout(outer_layout)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_dashboard()

    def load_dashboard(self):
        self._refresh_kpi_cards()
        self._refresh_summary_cards()

    def _refresh_kpi_cards(self):
        for i in reversed(range(self.stats_section_layout.count())):
            item = self.stats_section_layout.takeAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        self.kpi_cards = []
        for index, kpi in enumerate(self.dashboard_service.get_kpi_items()):
            card = StatCard(
                title=kpi["title"],
                value=kpi["value"],
                subtitle=kpi["subtitle"],
                accent=kpi.get("accent", "#2383e2"),
            )
            card.clicked.connect(lambda k=kpi: self.on_kpi_card_clicked(k))
            self.kpi_cards.append(card)
            self.stats_section_layout.addWidget(card, 0, index)

        self.stats_section_layout.setColumnStretch(0, 1)
        self.stats_section_layout.setColumnStretch(1, 1)
        self.stats_section_layout.setColumnStretch(2, 1)
        self.stats_section_layout.setColumnStretch(3, 1)

    def _refresh_summary_cards(self):
        for i in reversed(range(self.summary_layout.count())):
            item = self.summary_layout.takeAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        self.summary_cards = []
        for summary in self.dashboard_service.get_summary_items():
            card = StatCard(
                title=summary["title"],
                value=summary["value"],
                subtitle=summary["subtitle"],
                accent=summary.get("accent", "#7f8c8d"),
            )
            self.summary_cards.append(card)
            self.summary_layout.addWidget(card)

    def on_kpi_card_clicked(self, kpi: dict):
        if not self.navigate_callback:
            return

        page = kpi.get("page")
        filters = kpi.get("filters") or {}
        self.navigate_callback(page, filter_context=filters)
