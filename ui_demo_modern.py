from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QSizePolicy,
)
import sys

APP_STYLE = """
QMainWindow, QWidget {
    background-color: #eff6f8;
    color: #22313f;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 14px;
}

QFrame#Card, QFrame#TopBarCard {
    background: #ffffff;
    border: 1px solid rgba(34, 49, 63, 0.08);
    border-radius: 20px;
}

QFrame#TopBarCard {
    background: rgba(255, 255, 255, 0.92);
}

QLabel#PageTitle {
    font-size: 26px;
    font-weight: 700;
    color: #172930;
}

QLabel#PageSubtitle {
    color: #5c6b75;
    font-size: 13px;
}

QLabel#SectionTitle {
    font-size: 17px;
    font-weight: 700;
    color: #1f3644;
}

QLabel#SectionDescription {
    color: #5d6d76;
    font-size: 13px;
}

QLabel#KpiValue {
    font-size: 28px;
    font-weight: 700;
    color: #0f4f4a;
}

QLabel#KpiLabel {
    font-size: 13px;
    color: #5c6c75;
}

QLabel#KpiSubtitle {
    font-size: 12px;
    color: #6d7f88;
}

QPushButton {
    min-height: 44px;
    padding: 0 18px;
    border-radius: 16px;
    border: none;
    background: #e8f3f2;
    color: #1f4f4b;
    font-weight: 600;
}

QPushButton:hover {
    background: #d7ebea;
}

QPushButton:pressed {
    background: #c8e2e0;
}

QPushButton#PrimaryButton {
    background: #157d74;
    color: #ffffff;
}

QPushButton#PrimaryButton:hover {
    background: #0f6a62;
}

QPushButton#SecondaryButton {
    background: #365f8b;
    color: #ffffff;
}

QPushButton#SecondaryButton:hover {
    background: #2e5175;
}

QPushButton#SoftButton {
    background: #f3faf9;
    color: #11726e;
    border: 1px solid #cfe8e5;
}

QPushButton#SoftButton:hover {
    background: #e5f2ef;
}

QTableWidget {
    background: #ffffff;
    border: none;
    border-radius: 18px;
    gridline-color: #e5eef2;
    selection-background-color: #d4eef0;
    selection-color: #172930;
}

QHeaderView::section {
    background: #f4fafc;
    color: #43606f;
    font-weight: 700;
    border: none;
    border-bottom: 1px solid #dde7eb;
    padding: 14px 12px;
}

QTableWidget::item {
    padding: 14px 12px;
    border-bottom: 1px solid #f0f4f6;
}

QScrollBar:vertical {
    width: 10px;
    background: transparent;
    margin: 8px 0 8px 0;
}

QScrollBar::handle:vertical {
    background: #c4d5dc;
    border-radius: 5px;
    min-height: 30px;
}

QLabel#BadgeSuccess {
    background: #e6f5ef;
    color: #196551;
    border: 1px solid #bde6d2;
    border-radius: 12px;
    padding: 6px 12px;
    font-weight: 700;
}

QLabel#BadgeWarning {
    background: #fff4e8;
    color: #8a5d22;
    border: 1px solid #f2d3b0;
    border-radius: 12px;
    padding: 6px 12px;
    font-weight: 700;
}

QLabel#BadgeDanger {
    background: #fde8e8;
    color: #9a3b3b;
    border: 1px solid #efc7c7;
    border-radius: 12px;
    padding: 6px 12px;
    font-weight: 700;
}
"""


class KpiCard(QFrame):
    def __init__(self, title: str, value: str, subtitle: str, accent: bool = False):
        super().__init__()
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
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
        if accent:
            self.setStyleSheet("QFrame#Card { background: #f0fbf9; border-color: #c8e7e1; }")


class ModernDashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Anspruchssystem – Modernes Dashboard")
        self.resize(1480, 980)
        self.init_ui()

    def init_ui(self):
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 24, 24, 24)
        body_layout.setSpacing(20)

        body_layout.addWidget(self.build_topbar())
        body_layout.addLayout(self.build_kpi_grid())
        body_layout.addWidget(self.build_main_table())

        self.setCentralWidget(body)

    def build_topbar(self) -> QFrame:
        topbar = QFrame()
        topbar.setObjectName("TopBarCard")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(24, 22, 24, 22)
        topbar_layout.setSpacing(18)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(6)

        page_title = QLabel("Dashboard")
        page_title.setObjectName("PageTitle")

        page_subtitle = QLabel("Übersicht, Kennzahlen und schnell erreichbare Aktionen für Fachprozesse")
        page_subtitle.setObjectName("PageSubtitle")
        page_subtitle.setWordWrap(True)

        title_layout.addWidget(page_title)
        title_layout.addWidget(page_subtitle)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)

        search_input = QLineEdit()
        search_input.setPlaceholderText("Suche im System...")
        search_input.setFixedWidth(320)
        search_input.setMinimumHeight(44)

        location_select = QComboBox()
        location_select.addItems(["Alle Standorte", "Bern-Mitte", "Wien", "Zürich"])
        location_select.setFixedWidth(200)
        location_select.setMinimumHeight(44)

        new_button = QPushButton("Neuer Antrag")
        new_button.setObjectName("PrimaryButton")
        new_button.setCursor(Qt.CursorShape.PointingHandCursor)

        controls_layout.addWidget(search_input)
        controls_layout.addWidget(location_select)
        controls_layout.addWidget(new_button)

        topbar_layout.addLayout(title_layout, 1)
        topbar_layout.addLayout(controls_layout)
        return topbar

    def build_kpi_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(16)

        grid.addWidget(KpiCard("Offene Prüfungen", "18", "5 davon heute fällig", accent=True), 0, 0)
        grid.addWidget(KpiCard("Aktive Karten", "126", "12 laufen in 30 Tagen aus"), 0, 1)
        grid.addWidget(KpiCard("Dokumente offen", "9", "Nachweise fehlen oder sind unklar"), 0, 2)
        grid.addWidget(KpiCard("Meine Aufgaben", "14", "3 kritisch, 4 heute fällig"), 0, 3)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 1)
        return grid

    def build_main_table(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(18)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        header_texts = QVBoxLayout()
        header_texts.setSpacing(6)

        title = QLabel("Offene Anträge")
        title.setObjectName("SectionTitle")

        subtitle = QLabel("Tabellarische Übersicht mit sauberem Layout und klaren Aktionsbuttons in jeder Zeile.")
        subtitle.setObjectName("SectionDescription")
        subtitle.setWordWrap(True)

        header_texts.addWidget(title)
        header_texts.addWidget(subtitle)

        action_buttons = QHBoxLayout()
        action_buttons.setSpacing(10)

        filter_button = QPushButton("Filtern")
        filter_button.setObjectName("SoftButton")
        filter_button.setCursor(Qt.CursorShape.PointingHandCursor)

        export_button = QPushButton("Export")
        export_button.setObjectName("SecondaryButton")
        export_button.setCursor(Qt.CursorShape.PointingHandCursor)

        action_buttons.addWidget(filter_button)
        action_buttons.addWidget(export_button)

        header_layout.addLayout(header_texts, 1)
        header_layout.addLayout(action_buttons)

        card_layout.addLayout(header_layout)
        card_layout.addWidget(self.build_table())
        return card

    def build_table(self) -> QTableWidget:
        table = QTableWidget(5, 6)
        table.setHorizontalHeaderLabels(["Fallnummer", "Antragsteller", "Standort", "Status", "Datum", "Aktion"])
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setWordWrap(False)
        table.setCornerButtonEnabled(False)
        table.setSortingEnabled(False)
        table.setAlternatingRowColors(False)
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().setDefaultSectionSize(62)

        rows = [
            ("A-2026-001", "Anna Meier", "Bern-Mitte", "BEREIT ZUR PRÜFUNG", "20.05.2026"),
            ("A-2026-002", "Luca Huber", "Wien", "UNTERLAGEN FEHLEN", "19.05.2026"),
            ("A-2026-003", "Mila Schneider", "Bern-Mitte", "IN BEARBEITUNG", "18.05.2026"),
            ("A-2026-004", "Jonas Keller", "Zürich", "BERECHTIGT", "17.05.2026"),
            ("A-2026-005", "Lea Baumann", "Wien", "ABGELEHNT", "16.05.2026"),
        ]

        for row_index, (case, applicant, location, status, date_text) in enumerate(rows):
            table.setItem(row_index, 0, QTableWidgetItem(case))
            table.setItem(row_index, 1, QTableWidgetItem(applicant))
            table.setItem(row_index, 2, QTableWidgetItem(location))
            table.setItem(row_index, 4, QTableWidgetItem(date_text))

            status_label = QLabel(status)
            if status == "BERECHTIGT":
                status_label.setObjectName("BadgeSuccess")
            elif status == "ABGELEHNT":
                status_label.setObjectName("BadgeDanger")
            else:
                status_label.setObjectName("BadgeWarning")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setCellWidget(row_index, 3, status_label)

            action_cell = QWidget()
            action_layout = QHBoxLayout(action_cell)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(10)

            open_button = QPushButton("Öffnen")
            open_button.setObjectName("RowActionButton")
            open_button.setCursor(Qt.CursorShape.PointingHandCursor)
            open_button.setFixedHeight(36)

            details_button = QPushButton("Details")
            details_button.setObjectName("RowActionButton")
            details_button.setCursor(Qt.CursorShape.PointingHandCursor)
            details_button.setFixedHeight(36)

            action_layout.addWidget(open_button)
            action_layout.addWidget(details_button)
            action_layout.addStretch()

            table.setCellWidget(row_index, 5, action_cell)

            for col in range(6):
                item = table.item(row_index, col)
                if item:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        return table


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    window = ModernDashboardWindow()
    window.show()
    sys.exit(app.exec())
