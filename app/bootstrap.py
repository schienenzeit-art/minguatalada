import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QDialog

from app.config import WINDOW_WIDTH, WINDOW_HEIGHT
from app.container import build_service_container
from core.constants import APP_TITLE
from core.session import Session
from database.db import initialize_database

from ui.login.login_window import LoginWindow
from ui.shell.main_window import MainWindow


def load_theme() -> str:
    theme_path = Path(__file__).resolve().parent.parent / "ui" / "styles" / "theme.qss"
    if theme_path.exists():
        return theme_path.read_text(encoding="utf-8")
    return ""


def run_app() -> None:
    print("STEP 1")

    initialize_database()

    print("STEP 2")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setStyleSheet(load_theme())

    print("STEP 3")

    service_container = build_service_container()
    login_window = LoginWindow(auth_service=service_container.auth_service)

    print("STEP 4")

    result = login_window.exec()

    if result != QDialog.DialogCode.Accepted:
        print("LOGIN NOT ACCEPTED")
        sys.exit(0)

    user = Session.get_user()
    if user is None:
        print("NO AUTHENTICATED USER")
        sys.exit(0)

    print("STEP 5")

    main_window = MainWindow(service_container)

    main_window.setWindowTitle(APP_TITLE)

    print("LOGIN RESULT:", result)

    print("STEP 6")

    main_window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    # start application maximized so it adapts to the current screen
    main_window.showMaximized()

    print("STEP 7")

    sys.exit(app.exec())