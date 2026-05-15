from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)

from database.db import is_database_ready


class LoginWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.login_button = QPushButton("Anmelden")
        self.db_status_label = QLabel()
        self.setup_ui()
        self.connect_signals()
        self.update_database_status()

    def setup_ui(self) -> None:
        self.setMaximumWidth(420)

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Anspruchssystem Login")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Bitte Benutzername und Passwort eingeben.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.username_input.setPlaceholderText("Benutzername")

        self.password_input.setPlaceholderText("Passwort")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.db_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.db_status_label)
        layout.addSpacing(8)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addSpacing(8)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    def connect_signals(self) -> None:
        self.login_button.clicked.connect(self.on_login_clicked)
        self.password_input.returnPressed.connect(self.on_login_clicked)

    def update_database_status(self) -> None:
        if is_database_ready():
            self.db_status_label.setText("Datenbankstatus: bereit")
        else:
            self.db_status_label.setText("Datenbankstatus: Fehler")

    def on_login_clicked(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username:
            QMessageBox.warning(
                self,
                "Eingabe fehlt",
                "Bitte einen Benutzernamen eingeben."
            )
            self.username_input.setFocus()
            return

        if not password:
            QMessageBox.warning(
                self,
                "Eingabe fehlt",
                "Bitte ein Passwort eingeben."
            )
            self.password_input.setFocus()
            return

        QMessageBox.information(
            self,
            "Login-Test",
            f"Benutzer: {username}\nPasswort eingegeben: Ja"
        )

        self.username_input.clear()
        self.password_input.clear()
        self.username_input.setFocus()