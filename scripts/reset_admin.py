"""
Setzt das Admin-Passwort zurück und aktiviert den Benutzer.
Aufruf: python scripts/reset_admin.py
"""
import sqlite3
import bcrypt
import os
import sys

APP_DB = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Anspruchssystem", "system.db"
)
DEV_DB = os.path.join(os.path.dirname(__file__), "..", "data", "system.db")

db_path = APP_DB if os.path.exists(APP_DB) else DEV_DB

NEW_PASSWORD = "Admin2024!"

pw_hash = bcrypt.hashpw(NEW_PASSWORD.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

conn = sqlite3.connect(db_path)
conn.execute(
    "UPDATE users SET password_hash=?, is_active=1, failed_attempts=0, locked_until=NULL, must_change_password=0 WHERE username='admin'",
    (pw_hash,)
)
conn.commit()
rows = conn.execute("SELECT id, username, is_active FROM users WHERE username='admin'").fetchall()
conn.close()

if rows:
    print(f"Datenbank: {db_path}")
    print(f"Benutzer:  admin")
    print(f"Passwort:  {NEW_PASSWORD}")
    print(f"Aktiv:     {rows[0][2]}")
    print("OK – Admin-Konto wurde zurückgesetzt.")
else:
    print("FEHLER: Benutzer 'admin' nicht gefunden.")
    sys.exit(1)
