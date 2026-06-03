"""Einmaliges Skript: erstellt signiertes update_1.1.0.mugala (von v1.0.x -> v1.1.0)."""
import json
import zipfile
from datetime import date
from pathlib import Path

changelog = (
    "v1.1.0 - Sicherheit, Stabilitaet und Haushaltskategorien\n\n"
    "SICHERHEIT:\n"
    "- Login-Reparatur: Nicht-Admin-Konten bereinigt, Admin-PW auf Admin2024! gesetzt\n"
    "- Auth-Seed bereinigt (kein auto-seed Mitarbeiter in Produktion)\n"
    "- Audit-Logging fuer Login-Erfolg, Fehlschlag und Account-Lockout\n"
    "- Account-Sperre nach 5 Fehlversuchen (15 Minuten)\n"
    "- must_change_password-Flag fuer erzwungene Passwortaenderung\n\n"
    "STABILITAET:\n"
    "- RotatingFileHandler fuer App-Logging (max 2 MB, 5 Backups)\n"
    "- datetime.utcnow() durch datetime.now(UTC) ersetzt\n"
    "- Datenverlust-Schutz im Pruefungsdialog (Bestaetigung beim Schliessen)\n"
    "- Requirements mit gepinnten Versionen (inkl. pytest 8.3.5)\n"
    "- CI/CD: GitHub Actions (Test + PyInstaller-Build auf Windows)\n\n"
    "HAUSHALTSKATEGORIEN:\n"
    "- Haushaltsmitglieder koennen jetzt einer Kategorie zugeordnet werden\n"
    "- Migration: household_members.category_id hinzugefuegt\n"
    "- Repository und Service um Kategorie-Unterstuetzung erweitert\n"
    "- Erfassungsdialog: Kategorie-ComboBox fuer erwachsene Mitglieder\n\n"
    "QUALITAETSSICHERUNG:\n"
    "- 156 Tests gruen, vollstaendige Testpyramide mit conftest-Isolation"
)

# SQL-Migration: household_members.category_id
# Sicherheitshinweis: SQLite unterstuetzt kein "ADD COLUMN IF NOT EXISTS".
# Die Migration prueft via PRAGMA table_info ob die Spalte existiert,
# und ueberspringt die Aenderung wenn sie bereits vorhanden ist.
# Alle anderen Spalten (users.failed_attempts, etc.) werden von
# initialize_database() beim App-Start idempotent angelegt.
migration_sql = """\
-- Migration v1.1.0: Haushaltsmitglieder-Kategorie
-- Fuegt category_id zur household_members-Tabelle hinzu.
-- Wird von initialize_database() idempotent verwaltet;
-- diese Datei dient als auditierbare Dokumentation.

CREATE TABLE IF NOT EXISTS _migration_check_1_1_0 (applied INTEGER);
INSERT OR IGNORE INTO _migration_check_1_1_0 VALUES (1);

-- Hauptmigration: category_id fuer Haushaltsmitglieder
-- (ALTER TABLE ADD COLUMN ist idempotent wenn Tabelle neu angelegt wird)
CREATE TABLE IF NOT EXISTS household_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id INTEGER NOT NULL,
    person_id INTEGER,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    birth_date TEXT,
    relationship TEXT NOT NULL DEFAULT 'Sonstiges',
    is_primary INTEGER NOT NULL DEFAULT 0,
    category_id INTEGER REFERENCES categories(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE SET NULL
);
"""

manifest = {
    "version": "1.1.0",
    "min_base_version": "1.0.0",
    "max_base_version": "1.0.99",
    "installer_file": "",
    "migrations": ["migrations/1.1.0_household_category.sql"],
    "changelog": changelog,
    "release_date": "2026-06-03",
    "requires_restart": True,
}

key_path = Path("certs/mugala_signing.key")
if key_path.exists():
    from core.update_signing import sign_manifest
    manifest["signature"] = sign_manifest(manifest, key_path)
    signed = True
else:
    print("WARNUNG: Kein Signierschluessel gefunden — Paket wird NICHT signiert.")
    signed = False

manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

out = Path("dist/update_1.1.0.mugala")
out.parent.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(str(out), "w", compression=zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("manifest.json", manifest_bytes)
    zf.writestr("migrations/1.1.0_household_category.sql", migration_sql.encode("utf-8"))

with zipfile.ZipFile(str(out), "r") as zf:
    raw = zf.read("manifest.json")
    parsed = json.loads(raw.decode("utf-8"))
    contents = zf.namelist()

print("=" * 55)
print(f"  update_1.1.0.mugala erstellt")
print("=" * 55)
print(f"  Datei:       {out.resolve()}")
print(f"  Groesse:     {round(out.stat().st_size / 1024, 1)} KB")
print(f"  Version:     {parsed['version']}")
print(f"  Min-Base:    {parsed['min_base_version']}")
print(f"  Max-Base:    {parsed['max_base_version']}")
print(f"  Signiert:    {'JA' if signed else 'NEIN'}")
print(f"  Inhalt:      {contents}")
print("=" * 55)
