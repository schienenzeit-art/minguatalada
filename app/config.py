import os
import sys
from datetime import timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


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

# ── PostgreSQL connection ─────────────────────────────────────────────────────
# Set DATABASE_URL to switch from SQLite to PostgreSQL.
# Format: postgresql://user:password@host:port/dbname
# Individual params (DB_HOST etc.) are used as fallback if DATABASE_URL is unset.

def _build_database_url() -> str | None:
    """Return DATABASE_URL from env, or build one from individual params."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    host = os.environ.get("DB_HOST", "").strip()
    if not host:
        return None
    port = os.environ.get("DB_PORT", "5432").strip()
    name = os.environ.get("DB_NAME", "minguatalada").strip()
    user = os.environ.get("DB_USER", "").strip()
    password = os.environ.get("DB_PASSWORD", "").strip()
    if not user:
        return None
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL: str | None = _build_database_url()