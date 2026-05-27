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
    from app.config import RESOURCE_DIR
    theme_path = RESOURCE_DIR / "ui" / "styles" / "theme.qss"
    if theme_path.exists():
        return theme_path.read_text(encoding="utf-8")
    return ""


def _app_icon():
    """Lädt das App-Icon aus assets/logo.ico (oder .png als Fallback)."""
    from PyQt6.QtGui import QIcon
    from app.config import RESOURCE_DIR
    for name in ("logo.ico", "logo.png"):
        path = RESOURCE_DIR / "assets" / name
        if path.exists():
            return QIcon(str(path))
    return QIcon()


def run_app() -> None:
    initialize_database()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setWindowIcon(_app_icon())
    app.setStyleSheet(load_theme())

    service_container = build_service_container()
    login_window = LoginWindow(auth_service=service_container.auth_service)

    result = login_window.exec()

    if result != QDialog.DialogCode.Accepted:
        sys.exit(0)

    user = Session.get_user()
    if user is None:
        sys.exit(0)

    main_window = MainWindow(service_container)
    main_window.setWindowTitle(APP_TITLE)
    main_window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    main_window.showMaximized()

    sys.exit(app.exec())