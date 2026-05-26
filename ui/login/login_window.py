from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)

from services.auth_service import AuthService
from core.session import Session


class LoginWindow(QDialog):
    def __init__(self, auth_service: AuthService | None = None):
        super().__init__()
        self.auth_service = auth_service or AuthService()
        self.current_user = None
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("loginDialog")
        self.setWindowTitle("Anspruchssystem Anmeldung")
        self.setMinimumSize(420, 460)
        self.setModal(True)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("LoginCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(18)

        title_label = QLabel("Willkommen zurück")
        title_label.setObjectName("PageTitle")
        subtitle_label = QLabel("Melden Sie sich mit Ihren Zugangsdaten an, um das Anspruchssystem zu öffnen.")
        subtitle_label.setObjectName("PageSubtitle")
        subtitle_label.setWordWrap(True)

        self.username_input = QLineEdit()
        self.username_input.setObjectName("loginInput")
        self.username_input.setPlaceholderText("Benutzername")

        self.password_input = QLineEdit()
        self.password_input.setObjectName("loginInput")
        self.password_input.setPlaceholderText("Passwort")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.login_button = QPushButton("Anmelden")
        self.login_button.setObjectName("PrimaryButton")
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.clicked.connect(self.on_login_clicked)

        card_layout.addWidget(title_label)
        card_layout.addWidget(subtitle_label)
        card_layout.addWidget(QLabel("Benutzername"))
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(QLabel("Passwort"))
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.login_button)

        footer_spacer = QHBoxLayout()
        footer_spacer.addStretch()
        card_layout.addLayout(footer_spacer)

        root_layout.addStretch()
        root_layout.addWidget(card)
        root_layout.addStretch()

        self.setLayout(root_layout)

    def on_login_clicked(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Eingabe fehlt", "Bitte Benutzername und Passwort eingeben.")
            return

        result = self.auth_service.login(username, password)

        if not result["success"]:
            QMessageBox.warning(self, "Anmeldung fehlgeschlagen", result["message"])
            return

        self.current_user = result["user"]
        Session.set_user(result["user"])
        self.accept()