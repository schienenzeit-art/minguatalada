from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSizePolicy
from ui.components.page_header import PageHeader


class AnspruchspruefungAppPage(QWidget):
    def __init__(self, navigate_callback=None):
        super().__init__()
        self.navigate_callback = navigate_callback
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("anspruchspruefungPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header = PageHeader(
            title="Anspruchsprüfung",
            subtitle="Zentraler Einstieg für Anträge, Prüfung, Berechnung und Kartenableitung",
        )
        layout.addWidget(header)

        intro = QLabel(
            "Hier ist der fachliche Arbeitsbereich für die Anspruchsprüfung. "
            "Öffnen Sie Anträge, prüfen Sie Fälle, erstellen Sie Karten und behalten Sie den Prüfstatus im Blick."
        )
        intro.setWordWrap(True)
        intro.setObjectName("pageSectionText")
        layout.addWidget(intro)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(16)

        self.add_navigation_button(button_layout, "Anträge & Prüfungen", "claims")
        self.add_navigation_button(button_layout, "Karten & Ableitungen", "cards")
        self.add_navigation_button(button_layout, "Prüfungs‑Board", "tasks")

        layout.addLayout(button_layout)
        layout.addStretch()
        self.setLayout(layout)

    def add_navigation_button(self, layout, label: str, page_key: str):
        button = QPushButton(label)
        button.setObjectName("PrimaryButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        button.clicked.connect(lambda: self.navigate_callback(page_key) if self.navigate_callback else None)
        layout.addWidget(button)
