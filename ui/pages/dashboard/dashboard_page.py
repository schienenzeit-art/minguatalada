from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont

from services.dashboard_service import DashboardService
from ui.components.page_header import PageHeader


class ClickableCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class DashboardPage(QWidget):
    def __init__(self, dashboard_service: DashboardService | None = None, navigate_callback=None):
        super().__init__()
        self.dashboard_service = dashboard_service or DashboardService()
        self.navigate_callback = navigate_callback
        self.setup_ui()
        self.load_dashboard()

    def setup_ui(self):
        self.setObjectName("dashboardPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        layout.addWidget(self.build_topbar())
        layout.addLayout(self.build_kpi_grid())
        layout.addWidget(self.build_main_card())

        self.setLayout(layout)

    def build_topbar(self) -> QFrame:
        topbar = QFrame()
        topbar.setObjectName("TopBarCard")
        topbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(24, 24, 24, 24)
        topbar_layout.setSpacing(18)

        title_column = QVBoxLayout()
        title_column.setSpacing(6)

        title_label = QLabel("Dashboard")
        title_label.setObjectName("PageTitle")

        subtitle_label = QLabel("Moderne Übersicht für Ansprüche, Karten und operative Kennzahlen")
        subtitle_label.setObjectName("PageSubtitle")
        subtitle_label.setWordWrap(True)

        title_column.addWidget(title_label)
        title_column.addWidget(subtitle_label)

        actions = QHBoxLayout()
        actions.setSpacing(12)

        search_input = QLineEdit()
        search_input.setPlaceholderText("Suche im System...")
        search_input.setFixedWidth(320)
        search_input.setMinimumHeight(44)

        location_select = QComboBox()
        location_select.addItems(["Alle Standorte", "Bern-Mitte", "Wien", "Zürich"])
        location_select.setFixedWidth(200)
        location_select.setMinimumHeight(44)

        primary_button = QPushButton("Neuer Antrag")
        primary_button.setObjectName("PrimaryButton")
        primary_button.setCursor(Qt.CursorShape.PointingHandCursor)

        actions.addWidget(search_input)
        actions.addWidget(location_select)
        actions.addWidget(primary_button)

        topbar_layout.addLayout(title_column, 1)
        topbar_layout.addLayout(actions)
        return topbar

    def build_kpi_grid(self) -> QGridLayout:
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(16)
        self.kpi_grid.setContentsMargins(0, 0, 0, 0)
        return self.kpi_grid

    def build_main_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(18)

        header = QHBoxLayout()
        header.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(6)

        title = QLabel("Offene Anträge")
        title.setObjectName("SectionTitle")

        subtitle = QLabel("Klares Tabellenlayout mit gleichen Zeilenhöhen und direkter Navigation per Klick auf Fallnummer oder Antragsteller.")
        subtitle.setObjectName("SectionDescription")
        subtitle.setWordWrap(True)

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        actions = QHBoxLayout()
        actions.setSpacing(10)

        filter_button = QPushButton("Filtern")
        filter_button.setObjectName("SoftButton")
        filter_button.setCursor(Qt.CursorShape.PointingHandCursor)

        export_button = QPushButton("Export")
        export_button.setObjectName("SecondaryButton")
        export_button.setCursor(Qt.CursorShape.PointingHandCursor)

        actions.addWidget(filter_button)
        actions.addWidget(export_button)

        header.addLayout(title_box, 1)
        header.addLayout(actions)

        card_layout.addLayout(header)
        card_layout.addWidget(self.build_table())
        return card

    def build_table(self) -> QTableWidget:
        self.table = QTableWidget(5, 5)
        self.table.setHorizontalHeaderLabels([
            "Fallnummer", "Antragsteller", "Standort", "Status", "Datum"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setWordWrap(False)
        self.table.setCornerButtonEnabled(False)
        self.table.setSortingEnabled(False)
        self.table.setAlternatingRowColors(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setMinimumSectionSize(120)
        self.table.horizontalHeader().resizeSection(3, 200)
        self.table.cellClicked.connect(self.on_table_cell_clicked)
        self.table.verticalHeader().setDefaultSectionSize(62)
        return self.table

    def showEvent(self, event):
        super().showEvent(event)
        self.load_dashboard()

    def load_dashboard(self):
        self._refresh_kpi_cards()
        self._refresh_table_rows()

    def _refresh_kpi_cards(self):
        while self.kpi_grid.count():
            item = self.kpi_grid.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        items = self.dashboard_service.get_kpi_items()
        for index, kpi in enumerate(items):
            card = self.build_kpi_card(
                title=kpi["title"],
                value=kpi["value"],
                subtitle=kpi["subtitle"],
                page=kpi.get("page"),
                filters=kpi.get("filters"),
                accent=bool(index == 0),
            )
            self.kpi_grid.addWidget(card, 0, index)

        for i in range(len(items)):
            self.kpi_grid.setColumnStretch(i, 1)

    def build_kpi_card(
        self,
        title: str,
        value: str,
        subtitle: str,
        page: str | None = None,
        filters: dict | None = None,
        accent: bool = False,
    ) -> QFrame:
        card = ClickableCard()
        card.setObjectName("Card")
        if accent:
            card.setProperty("accent", True)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        if page:
            card.clicked.connect(
                lambda page=page, filters=filters: self.navigate_callback(page, filters)
                if self.navigate_callback
                else None
            )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        label = QLabel(title)
        label.setObjectName("KpiLabel")

        value_label = QLabel(value)
        value_label.setObjectName("KpiValue")

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("KpiSubtitle")
        subtitle_label.setWordWrap(True)

        layout.addWidget(label)
        layout.addWidget(value_label)
        layout.addWidget(subtitle_label)
        return card

    def _refresh_table_rows(self):
        sample_rows = [
            ("A-2026-001", "Anna Meier", "Bern-Mitte", "BEREIT ZUR PRÜFUNG", "20.05.2026"),
            ("A-2026-002", "Luca Huber", "Wien", "UNTERLAGEN FEHLEN", "19.05.2026"),
            ("A-2026-003", "Mila Schneider", "Bern-Mitte", "IN BEARBEITUNG", "18.05.2026"),
            ("A-2026-004", "Jonas Keller", "Zürich", "BERECHTIGT", "17.05.2026"),
            ("A-2026-005", "Lea Baumann", "Wien", "ABGELEHNT", "16.05.2026"),
        ]

        self.table.setRowCount(len(sample_rows))
        for row_index, (case, applicant, location, status, date_text) in enumerate(sample_rows):
            self.table.setItem(row_index, 0, self._create_clickable_item(case))
            self.table.setItem(row_index, 1, self._create_clickable_item(applicant))
            self.table.setItem(row_index, 2, QTableWidgetItem(location))
            self.table.setItem(row_index, 4, QTableWidgetItem(date_text))

            status_label = QLabel(status)
            if status == "BERECHTIGT":
                status_label.setObjectName("BadgeSuccess")
            elif status == "ABGELEHNT":
                status_label.setObjectName("BadgeDanger")
            else:
                status_label.setObjectName("BadgeWarning")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row_index, 3, status_label)
            self.table.setRowHeight(row_index, 64)

    def _create_clickable_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setForeground(QBrush(QColor("#1B61B2")))
        font = item.font()
        font.setUnderline(True)
        item.setFont(font)
        item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        return item

    def on_table_cell_clicked(self, row: int, column: int) -> None:
        if column not in (0, 1):
            return
        case_item = self.table.item(row, 0)
        applicant_item = self.table.item(row, 1)
        if case_item is None:
            return
        search_text = case_item.text() if column == 0 else (applicant_item.text() if applicant_item else "")
        if not search_text or not self.navigate_callback:
            return
        self.navigate_callback("claims", {"search_text": search_text})
