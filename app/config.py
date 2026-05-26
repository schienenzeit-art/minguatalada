print("CONFIG FILE LOADED")
print(__file__)
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "system.db"
DOCUMENTS_DIR = DATA_DIR / "documents"

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
import os
from datetime import timedelta

# Web / API configuration
SECRET_KEY = os.environ.get("APP_SECRET_KEY", "please-set-a-secure-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY = timedelta(hours=8)