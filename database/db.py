from pathlib import Path
from app.config import DATA_DIR

def ensure_data_dir() -> None:
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)