"""
M5 – Audit-Protokoll
Zeigt alle Systemaktionen mit Filter nach Bereich, Benutzer und Datum.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QLineEdit,
)
from ui.components.page_header import PageHeader
from services.audit_service import AuditService
from services.user_service import UserService


_OBJECT_TYPE_LABELS = {
    "claim":       "Antrag",
    "claims":      "Antrag",
    "person":      "Person",
    "persons":     "Person",
    "card":        "Karte",
    "cards":       "Karte",
    "document":    "Dokument",
    "documents":   "Dokument",
    "user":        "Benutzer",
    "users":       "Benutzer",
    "task":        "Aufgabe",
    "appointment": "Termin",
}


class AuditLogPage(QWidget):
    def __init__(
        self,
        audit_service: AuditService | None = None,
        user_service: UserService | None = None,
    ):
        super().__init__()
        self.svc      = audit_service or AuditService()
        self.usr_svc  = user_service or UserService()
        self._logs: list[dict] = []
        self._users: list[dict] = []
        self._page    = 0
        self._page_size = 100
        self._setup_ui()
        self._load_users()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            title="Audit-Protokoll",
            subtitle="Systemaktionen und Datenänderungen nachvollziehen.",
        ))

        # ── Filter-Leiste ──────────────────────────────────────────────────────
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        self._type_combo = QComboBox()
        self._type_combo.setMinimumWidth(160)
        self._type_combo.addItem("Alle Bereiche", None)
        for val, label in [
            ("claim", "Anträge"),
            ("person", "Personen"),
            ("card", "Karten"),
            ("document", "Dokumente"),
            ("user", "Benutzer"),
            ("task", "Aufgaben"),
            ("appointment", "Termine"),
        ]:
            self._type_combo.addItem(label, val)
        self._type_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(QLabel("Bereich:"))
        filter_row.addWidget(self._type_combo)

        self._user_combo = QComboBox()
        self._user_combo.setMinimumWidth(180)
        self._user_combo.addItem("Alle Benutzer", None)
        self._user_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(QLabel("Benutzer:"))
        filter_row.addWidget(self._user_combo)

        filter_row.addStretch()

        refresh_btn = QPushButton("Aktualisieren")
        refresh_btn.setObjectName("SoftButton")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)
        filter_row.addWidget(refresh_btn)

        layout.addLayout(filter_row)

        # ── Tabelle ────────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Zeitpunkt", "Benutzer", "Aktion", "Bereich", "ID", "Details"
        ])
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setMinimumHeight(300)
        layout.addWidget(self._table)

        # ── Paginierung ────────────────────────────────────────────────────────
        page_row = QHBoxLayout()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #9b9896; font-size: 12px;")
        page_row.addWidget(self._status_lbl, 1)

        self._prev_btn = QPushButton("← Zurück")
        self._prev_btn.setObjectName("SoftButton")
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev_btn.clicked.connect(self._prev_page)
        page_row.addWidget(self._prev_btn)

        self._page_lbl = QLabel("Seite 1")
        page_row.addWidget(self._page_lbl)

        self._next_btn = QPushButton("Weiter →")
        self._next_btn.setObjectName("SoftButton")
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(self._next_page)
        page_row.addWidget(self._next_btn)

        layout.addLayout(page_row)

    def _load_users(self):
        try:
            self._users = self.usr_svc.get_all_users()
        except Exception:
            self._users = []
        self._user_combo.blockSignals(True)
        for u in self._users:
            self._user_combo.addItem(u.get("full_name", u.get("username", "-")), u["id"])
        self._user_combo.blockSignals(False)

    def _on_filter_changed(self):
        self._page = 0
        self.refresh()

    def refresh(self):
        object_type = self._type_combo.currentData()
        user_id     = self._user_combo.currentData()
        offset      = self._page * self._page_size

        self._logs = self.svc.list_logs(
            object_type=object_type,
            user_id=user_id,
            limit=self._page_size,
            offset=offset,
        )
        total = self.svc.count(object_type=object_type, user_id=user_id)

        self._table.setRowCount(len(self._logs))
        for i, log in enumerate(self._logs):
            ts = log.get("timestamp", "")
            # Make timestamp more readable
            ts_display = ts.replace("T", " ")[:19] if ts else ""
            self._table.setItem(i, 0, QTableWidgetItem(ts_display))
            self._table.setItem(i, 1, QTableWidgetItem(log.get("user_name") or "System"))
            self._table.setItem(i, 2, QTableWidgetItem(log.get("action", "")))
            ot = log.get("object_type", "")
            self._table.setItem(i, 3, QTableWidgetItem(_OBJECT_TYPE_LABELS.get(ot, ot)))
            obj_id = log.get("object_id")
            self._table.setItem(i, 4, QTableWidgetItem(str(obj_id) if obj_id else "—"))
            self._table.setItem(i, 5, QTableWidgetItem(log.get("details") or ""))

        pages = max(1, (total + self._page_size - 1) // self._page_size)
        self._page_lbl.setText(f"Seite {self._page + 1} / {pages}")
        self._prev_btn.setEnabled(self._page > 0)
        self._next_btn.setEnabled((self._page + 1) < pages)
        self._status_lbl.setText(f"{total} Einträge gesamt.")

    def _prev_page(self):
        if self._page > 0:
            self._page -= 1
            self.refresh()

    def _next_page(self):
        self._page += 1
        self.refresh()
