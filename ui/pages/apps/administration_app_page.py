from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QGridLayout, QFrame, QSizePolicy,
)
from ui.components.page_header import PageHeader


_NAV_GROUPS = [
    {
        "title": "Benutzer & Zugriff",
        "items": [
            ("Benutzerverwaltung",  "users"),
            ("Rollenverwaltung",    "roles"),
            ("Mandanten",           "mandants"),
        ],
    },
    {
        "title": "Stammdaten",
        "items": [
            ("Standorte",           "locations"),
            ("Einstellungen",       "settings"),
            ("Daten-Import",        "import"),
        ],
    },
    {
        "title": "Vorlagen & Listen",
        "items": [
            ("Dokumentvorlagen",        "document_templates"),
            ("Unterlagen-Checklisten",  "checklist_templates"),
            ("Serienbriefe",            "serial_letters"),
        ],
    },
    {
        "title": "Compliance & Audit",
        "items": [
            ("Archiv-Regeln",   "archive_rules"),
            ("Audit-Protokoll", "audit_log"),
        ],
    },
]


class AdministrationAppPage(QWidget):
    def __init__(self, navigate_callback=None):
        super().__init__()
        self.navigate_callback = navigate_callback
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("administrationPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        layout.addWidget(PageHeader(
            title="Administration",
            subtitle="Benutzerkonten, Stammdaten, Vorlagen und Systemkonfiguration verwalten.",
        ))

        grid = QGridLayout()
        grid.setSpacing(16)

        for col, group in enumerate(_NAV_GROUPS):
            card = QFrame()
            card.setObjectName("Card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(10)

            title_lbl = QLabel(f"<b>{group['title']}</b>")
            title_lbl.setStyleSheet("font-size: 13px; color: #333;")
            card_layout.addWidget(title_lbl)

            for label, page_key in group["items"]:
                btn = QPushButton(label)
                btn.setObjectName("SoftButton")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                btn.clicked.connect(
                    lambda checked=False, k=page_key: self.navigate_callback(k) if self.navigate_callback else None
                )
                card_layout.addWidget(btn)

            card_layout.addStretch()
            grid.addWidget(card, 0, col)

        layout.addLayout(grid)
        layout.addStretch()

    def add_navigation_button(self, layout, label: str, page_key: str):
        button = QPushButton(label)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        button.clicked.connect(lambda: self.navigate_callback(page_key) if self.navigate_callback else None)
        layout.addWidget(button)
