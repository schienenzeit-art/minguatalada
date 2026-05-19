from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QMessageBox, QApplication


class HeaderBar(QWidget):
    def __init__(self, user: dict | None = None):
        super().__init__()
        self.user = user or {}
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("headerBar")
        self.setStyleSheet(
            "#headerBar { background-color: #f5f5f5; border-bottom: 1px solid #cccccc; }"
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)

        title_label = QLabel("Anspruchssystem")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        user_label = QLabel(
            f"Benutzer: {self.user.get('full_name', 'Unbekannt')} | "
            f"Rolle: {self.user.get('role_name', '-')} | "
            f"Standort: {self.user.get('location_name', '-')}"
        )
        user_label.setStyleSheet("color: #333333;")

        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(user_label)

        self.logout_button = QPushButton("Abmelden")
        self.logout_button.clicked.connect(self.on_logout_clicked)
        layout.addWidget(self.logout_button)

        self.setLayout(layout)

    def on_logout_clicked(self):
        answer = QMessageBox.question(
            self,
            "Abmelden",
            "Möchten Sie sich abmelden und die Anwendung schließen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            QApplication.quit()
