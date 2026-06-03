import logging
import logging.handlers
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QDialog

from app.config import WINDOW_WIDTH, WINDOW_HEIGHT, DATA_DIR
from app.container import build_service_container
from core.constants import APP_TITLE
from core.session import Session
from database.db import initialize_database, check_database_health

from ui.login.login_window import LoginWindow
from ui.shell.main_window import MainWindow


def setup_logging() -> None:
    """Richtet das zentrale Logging ein: RotatingFileHandler + Console."""
    log_dir = Path(DATA_DIR) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Bereits konfiguriert (z. B. in Tests)? Handler nicht doppelt hinzufügen.
    if root_logger.handlers:
        return

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotierende Logdatei: max 2 MB, 5 Backups → max ~10 MB
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    # Console (nur für Entwicklungsmodus, nicht im Frozen-Bundle nötig)
    if not getattr(sys, "frozen", False):
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        console.setLevel(logging.DEBUG)
        root_logger.addHandler(console)

    logging.getLogger(__name__).info("Logging initialisiert — Log-Datei: %s", log_file)


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
    setup_logging()
    initialize_database()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setWindowIcon(_app_icon())
    app.setStyleSheet(load_theme())

    ok, health_messages = check_database_health()
    if not ok:
        from PyQt6.QtWidgets import QMessageBox
        detail = "\n".join(f"• {m}" for m in health_messages)
        QMessageBox.critical(
            None,
            "Datenbankfehler — Min Guata Lada",
            f"Die Datenbank ist beschädigt oder nicht erreichbar:\n\n{detail}\n\n"
            "Bitte ein Backup über die Einstellungen wiederherstellen\n"
            "oder den Support kontaktieren.",
        )
        sys.exit(1)

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