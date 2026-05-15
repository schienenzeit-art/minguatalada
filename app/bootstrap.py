import sys
from PyQt6.QtWidgets import QApplication
from app.config import APP_NAME, WINDOW_WIDTH, WINDOW_HEIGHT
from database.db import ensure_data_dir
from ui.shell.main_window import MainWindow

def run_app() -> None:
    ensure_data_dir()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    window = MainWindow()
    window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    window.show()

    sys.exit(app.exec())