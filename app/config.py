print("CONFIG FILE LOADED")
print(__file__)
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "system.db"
DOCUMENTS_DIR = DATA_DIR / "documents"

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800