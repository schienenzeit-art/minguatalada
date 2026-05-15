from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton

class LoginWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Login")
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        title = QLabel("Anspruchssystem Login")
        username = QLineEdit()
        username.setPlaceholderText("Benutzername")

        password = QLineEdit()
        password.setPlaceholderText("Passwort")
        password.setEchoMode(QLineEdit.EchoMode.Password)

        login_button = QPushButton("Anmelden")

        layout.addWidget(title)
        layout.addWidget(username)
        layout.addWidget(password)
        layout.addWidget(login_button)

        self.setLayout(layout)