import sqlite3, os
db_path = r"c:\Users\Projektleiter\Desktop\anspruchssystem\data\anspruchssystem.db"
if not os.path.exists(db_path):
    print("Datenbank nicht gefunden:", db_path)
else:
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT id, username, full_name, role, is_active FROM users").fetchall()
    if not rows:
        print("Keine Benutzer in der Datenbank.")
    for r in rows:
        aktiv = "JA" if r[4] else "NEIN"
        print(f"ID={r[0]}  Benutzername={r[1]}  Name={r[2]}  Rolle={r[3]}  Aktiv={aktiv}")
    conn.close()
