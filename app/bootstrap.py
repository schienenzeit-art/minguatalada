import sys

from PyQt6.QtWidgets import QApplication

from app.config import WINDOW_WIDTH, WINDOW_HEIGHT
from core.constants import APP_TITLE
from database.db import initialize_database
from ui.shell.main_window import MainWindow


def run_app() -> None:
    initialize_database()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)

    window = MainWindow()
    window.setWindowTitle(APP_TITLE)
    window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()