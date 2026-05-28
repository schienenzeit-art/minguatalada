import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QFrame,
    QSizePolicy,
    QDialog,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPixmap


def _logo_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parent.parent.parent.parent
    return base / "assets" / "logo.png"

from services.dashboard_service import DashboardService
from ui.pages.case_create_page import CaseCreateDialog
from ui.components.page_header import PageHeader
from ui.components.table_widget import TableWidget
from core.claim_status import ClaimStatus


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
        topbar_layout.setContentsMargins(24, 16, 24, 16)
        topbar_layout.setSpacing(18)

        # ── Logo ──────────────────────────────────────────────────────────────
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        lp = _logo_path()
        if lp.exists():
            pix = QPixmap(str(lp)).scaled(
                160, 72,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_lbl.setPixmap(pix)
        logo_lbl.setFixedWidth(170)
        topbar_layout.addWidget(logo_lbl)

        # Trennlinie
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #e0e0e0; max-width: 1px;")
        topbar_layout.addWidget(sep)

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

        # populate location select from service (avoid hardcoded demo locations)
        self.location_select = QComboBox()
        self.location_select.setFixedWidth(200)
        self.location_select.setMinimumHeight(44)
        self.location_select.addItem("Alle Standorte", None)
        try:
            locations = self.dashboard_service.location_service.list_active_locations()
            for loc in locations:
                self.location_select.addItem(loc.get("name", "?"), loc.get("id"))
        except Exception:
            # if location service fails, leave only 'Alle Standorte' to avoid hardcoded demo values
            pass

        primary_button = QPushButton("Neuer Antrag")
        primary_button.setObjectName("PrimaryButton")
        primary_button.setCursor(Qt.CursorShape.PointingHandCursor)
        primary_button.clicked.connect(self.open_new_case)

        actions.addWidget(search_input)
        actions.addWidget(self.location_select)
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

    def build_table(self) -> TableWidget:
        self.table = TableWidget(5)
        self.table.setHorizontalHeaderLabels([
            "Fallnummer", "Antragsteller", "Standort", "Status", "Datum"
        ])
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setMinimumSectionSize(120)
        self.table.horizontalHeader().resizeSection(3, 200)
        self.table.cellClicked.connect(self.on_table_cell_clicked)
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
                accent_color=kpi.get("accent", "#2383e2"),
            )
            self.kpi_grid.addWidget(card, 0, index)

        for i in range(len(items)):
            self.kpi_grid.setColumnStretch(i, 1)

    def open_new_case(self):
        dialog = CaseCreateDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # if case created, refresh dashboard
            self.load_dashboard()

    def build_kpi_card(
        self,
        title: str,
        value: str,
        subtitle: str,
        page: str | None = None,
        filters: dict | None = None,
        accent: bool = False,
        accent_color: str = "#2383e2",
    ) -> QFrame:
        card = ClickableCard()
        card.setObjectName("Card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        card.setMinimumHeight(138)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        if page:
            card.clicked.connect(
                lambda p=page, f=filters: self.navigate_callback(p, f)
                if self.navigate_callback
                else None
            )

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(18)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 18))
        card.setGraphicsEffect(shadow)

        outer = QVBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Farbiger Akzent-Strip oben
        strip = QFrame()
        strip.setFixedHeight(5)
        strip.setStyleSheet(
            f"background-color: {accent_color}; border: none; "
            f"border-radius: 16px 16px 0 0;"
        )
        outer.addWidget(strip)

        # Inhalt
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(4)

        label = QLabel(title)
        label.setObjectName("KpiLabel")
        label.setMinimumHeight(18)

        value_label = QLabel(value)
        value_label.setObjectName("KpiValue")
        value_label.setMinimumHeight(44)
        value_label.setStyleSheet(
            f"color: {accent_color}; font-size: 32px; font-weight: 800; "
            f"letter-spacing: -0.04em; background: transparent;"
        )

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("KpiSubtitle")
        subtitle_label.setWordWrap(True)
        subtitle_label.setMinimumHeight(18)

        layout.addWidget(label)
        layout.addWidget(value_label)
        layout.addSpacing(2)
        layout.addWidget(subtitle_label)
        layout.addStretch()
        outer.addWidget(inner)
        return card

    def _refresh_table_rows(self):
        recent_claims = self.dashboard_service.get_recent_claims(limit=5)
        self.table.setRowCount(len(recent_claims))

        for row_index, claim in enumerate(recent_claims):
            case = claim.get("case_number") or "-"
            applicant = claim.get("person_display_name") or claim.get("user_name") or "-"
            location = claim.get("location_name") or "-"
            raw_status = claim.get("status") or "-"
            status = ClaimStatus.get_display(raw_status)
            date_text = claim.get("created_at")[:10] if claim.get("created_at") else "-"

            self.table.setItem(row_index, 0, self._create_clickable_item(case))
            self.table.setItem(row_index, 1, self._create_clickable_item(applicant))
            self.table.setItem(row_index, 2, QTableWidgetItem(location))
            self.table.setItem(row_index, 4, QTableWidgetItem(date_text))

            status_label = QLabel(status)
            if raw_status in ("ANSPRUCHSBERECHTIGT", "HAERTEFALL"):
                status_label.setObjectName("BadgeSuccess")
            elif raw_status == "ABGELEHNT":
                status_label.setObjectName("BadgeDanger")
            elif raw_status == "ABGELAUFEN":
                status_label.setObjectName("BadgeWarning")
            else:
                status_label.setObjectName("BadgeSecondary")
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
