from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialogButtonBox,
)

from services.search_service import SearchService


class SearchResultDialog(QDialog):
    def __init__(self, query: str, search_service: SearchService | None = None, parent=None):
        super().__init__(parent)
        self.query = query
        self.search_service = search_service or SearchService()
        self.setWindowTitle(f"Suchergebnisse: {query}")
        self.setMinimumSize(760, 500)
        flags = self.windowFlags()
        flags |= Qt.WindowType.Window
        flags |= Qt.WindowType.WindowMinimizeButtonHint
        flags |= Qt.WindowType.WindowMaximizeButtonHint
        self.setWindowFlags(flags)
        self._setup_ui()
        self._run_search()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel(f"Suchergebnisse für: <b>{self.query}</b>")
        header.setStyleSheet("font-size: 14px; padding: 4px 0;")
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.persons_tab = self._make_table(["Name", "Adresse"])
        self.claims_tab = self._make_table(["Fallnummer", "Status", "Person", "Standort"])
        self.docs_tab = self._make_table(["Titel", "Typ", "Hochgeladen"])
        self.tabs.addTab(self.persons_tab, "Personen (0)")
        self.tabs.addTab(self.claims_tab, "Fälle (0)")
        self.tabs.addTab(self.docs_tab, "Dokumente (0)")
        layout.addWidget(self.tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _make_table(headers: list[str]) -> QTableWidget:
        tbl = QTableWidget(0, len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().hide()
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        return tbl

    def _run_search(self) -> None:
        results = self.search_service.search(self.query)

        persons = results.get("persons", [])
        self.tabs.setTabText(0, f"Personen ({len(persons)})")
        self.persons_tab.setRowCount(len(persons))
        for i, p in enumerate(persons):
            self.persons_tab.setItem(i, 0, QTableWidgetItem(p.get("name", "-")))
            self.persons_tab.setItem(i, 1, QTableWidgetItem(p.get("detail", "-")))

        claims = results.get("claims", [])
        self.tabs.setTabText(1, f"Fälle ({len(claims)})")
        self.claims_tab.setRowCount(len(claims))
        for i, c in enumerate(claims):
            self.claims_tab.setItem(i, 0, QTableWidgetItem(c.get("case_number", "-")))
            self.claims_tab.setItem(i, 1, QTableWidgetItem(c.get("status", "-")))
            self.claims_tab.setItem(i, 2, QTableWidgetItem(c.get("person", "-")))
            self.claims_tab.setItem(i, 3, QTableWidgetItem(c.get("location", "-")))

        docs = results.get("documents", [])
        self.tabs.setTabText(2, f"Dokumente ({len(docs)})")
        self.docs_tab.setRowCount(len(docs))
        for i, d in enumerate(docs):
            self.docs_tab.setItem(i, 0, QTableWidgetItem(d.get("title", "-")))
            self.docs_tab.setItem(i, 1, QTableWidgetItem(d.get("type", "-")))
            self.docs_tab.setItem(i, 2, QTableWidgetItem(d.get("uploaded_at", "-")))

        total = len(persons) + len(claims) + len(docs)
        if total == 0:
            self.tabs.widget(0).setDisabled(False)
