from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout

from ui.login.login_window import LoginWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Anspruchssystem")
        self.setup_ui()
        self.setup_statusbar()

    def setup_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)

        login_widget = LoginWindow()
        layout.addWidget(login_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        container.setLayout(layout)
        self.setCentralWidget(container)

    def setup_statusbar(self) -> None:
        self.statusBar().showMessage("Woche 1 Grundgerüst aktiv")