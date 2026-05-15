import sqlite3
from pathlib import Path

from app.config import DATA_DIR, DB_PATH


def ensure_data_dir() -> None:
    print("CREATE DATA DIR:", DATA_DIR)

    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

    print("DIR EXISTS:", DATA_DIR.exists())


def initialize_database() -> None:
    print("INIT DATABASE")

    ensure_data_dir()

    print("DB PATH:", DB_PATH)

    connection = sqlite3.connect(DB_PATH)

    print("CONNECTED")

    connection.close()

    print("DONE")


def is_database_ready() -> bool:
    try:
        ensure_data_dir()
        connection = sqlite3.connect(DB_PATH)
        connection.close()
        return True
    except sqlite3.Error:
        return False