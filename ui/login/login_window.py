from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
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
        self.setWindowTitle("Login")
        self.setMinimumWidth(320)

        layout = QVBoxLayout()

        title_label = QLabel("Anmeldung")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Benutzername")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Passwort")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.login_button = QPushButton("Anmelden")
        self.login_button.clicked.connect(self.on_login_clicked)

        layout.addWidget(title_label)
        layout.addWidget(QLabel("Benutzername"))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Passwort"))
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    def on_login_clicked(self):
        username = self.username_input.text()
        password = self.password_input.text()

        result = self.auth_service.login(username, password)

        print("LOGIN DEBUG RESULT:", result)   # 👈 WICHTIG

        if not result["success"]:
            QMessageBox.warning(self, "Login fehlgeschlagen", result["message"])
            return

        print("LOGIN SUCCESS - ACCEPT")

        self.current_user = result["user"]
        Session.set_user(result["user"])
       

        QMessageBox.information(self, "Erfolg", result["message"])
        self.accept()