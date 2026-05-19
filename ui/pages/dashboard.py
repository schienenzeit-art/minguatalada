from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
)

from ui.pages.claim_detail_page import ClaimDetailPage
from ui.pages.claim_evaluation_dialog import ClaimEvaluationDialog


class DashboardPage(QWidget):
    def __init__(self, user: dict):
        super().__init__()
        self.user = user or {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)

        title_label = QLabel("Dashboard")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")

        welcome_label = QLabel(f"Willkommen, {self.user.get('full_name', 'Benutzer')}")
        welcome_label.setStyleSheet("font-size: 14px; color: #333333;")

        role_label = QLabel(f"Rolle: {self.user.get('role_name', '-')}")
        location_label = QLabel(f"Standort: {self.user.get('location_name', '-')}")

        note_label = QLabel(
            "Hier sehen Sie den grundlegenden Status des Systems und können einen Anspruchsbeleg öffnen."
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #555555;")

        self.claim_button = QPushButton("Beispielanspruch anzeigen")
        self.claim_button.clicked.connect(self.open_example_claim)

        self.new_evaluation_button = QPushButton("Neue Prüfung starten")
        self.new_evaluation_button.clicked.connect(self.open_new_evaluation)

        layout.addWidget(title_label)
        layout.addWidget(welcome_label)
        layout.addWidget(role_label)
        layout.addWidget(location_label)
        layout.addWidget(note_label)
        layout.addWidget(self.claim_button)
        layout.addWidget(self.new_evaluation_button)
        layout.addStretch()

        self.setLayout(layout)

    def open_example_claim(self):
        dialog = ClaimDetailPage(claim_id=1)
        dialog.exec()

    def open_new_evaluation(self):
        dialog = ClaimEvaluationDialog(claim_id=None, claim_service=None)
        dialog.exec()