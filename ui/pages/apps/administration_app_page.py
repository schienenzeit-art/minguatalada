from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSizePolicy
from ui.components.page_header import PageHeader


class AdministrationAppPage(QWidget):
    def __init__(self, navigate_callback=None):
        super().__init__()
        self.navigate_callback = navigate_callback
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("administrationPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header = PageHeader(
            title="Administration",
            subtitle="Benutzerkonten, Standorte und Systemeinstellungen verwalten",
        )
        layout.addWidget(header)

        intro = QLabel(
            "Dieser Bereich fasst administrative Funktionen zusammen. "
            "Öffnen Sie Benutzerverwaltung, Standortdaten und die Systemeinstellungen."
        )
        intro.setWordWrap(True)
        intro.setObjectName("pageSectionText")
        layout.addWidget(intro)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(16)

        self.add_navigation_button(button_layout, "Benutzerverwaltung", "users")
        self.add_navigation_button(button_layout, "Standorte", "locations")
        self.add_navigation_button(button_layout, "Einstellungen", "settings")

        layout.addLayout(button_layout)
        layout.addStretch()
        self.setLayout(layout)

    def add_navigation_button(self, layout, label: str, page_key: str):
        button = QPushButton(label)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        button.clicked.connect(lambda: self.navigate_callback(page_key) if self.navigate_callback else None)
        layout.addWidget(button)
