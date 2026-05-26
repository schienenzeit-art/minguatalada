import os
import sys
from datetime import timedelta
from pathlib import Path


def _get_resource_dir() -> Path:
    """Verzeichnis mit gebündelten Programmressourcen (theme.qss etc.).
    Im PyInstaller-Bundle ist das sys._MEIPASS, sonst das Projektstamm-Verzeichnis."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def _get_data_dir() -> Path:
    """Schreibbares Datenverzeichnis fuer DB, Dokumente, PDFs.
    Im installierten Modus: %%LOCALAPPDATA%%/Anspruchssystem
    Im Entwicklungsmodus:   <Projektstamm>/data"""
    if getattr(sys, "frozen", False):
        local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        data_dir = local_app_data / "Anspruchssystem"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    return Path(__file__).resolve().parent.parent / "data"


BASE_DIR = Path(__file__).resolve().parent.parent
RESOURCE_DIR = _get_resource_dir()
DATA_DIR = _get_data_dir()
DB_PATH = DATA_DIR / "system.db"
DOCUMENTS_DIR = DATA_DIR / "documents"

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# Web / API configuration
SECRET_KEY = os.environ.get("APP_SECRET_KEY", "please-set-a-secure-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY = timedelta(hours=8)