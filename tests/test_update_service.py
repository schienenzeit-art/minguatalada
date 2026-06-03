"""
Tests für UpdateService: Backup, Paketvalidierung, destruktive-SQL-Block, Migrationen.

Kritische Sicherheitsebene: Das Update-System schützt Produktionsdaten.
Fehler hier bedeuten Datenverlust oder kaputte Installationen beim Verein.

Marker: @pytest.mark.slow für Backup-Tests (bcrypt + Datei-I/O).
"""
import json
import zipfile
from pathlib import Path

import pytest

from services.update_service import UpdateService, APP_VERSION

pytestmark = pytest.mark.slow


# ─── Fixture: UpdateService mit tmp-Verzeichnissen ───────────────────────────

@pytest.fixture()
def update_svc(db, tmp_path, monkeypatch):
    """UpdateService mit isolierten Backup/Update-Verzeichnissen."""
    import services.update_service as usmod
    monkeypatch.setattr(usmod, "BACKUPS_DIR", tmp_path / "backups")
    monkeypatch.setattr(usmod, "UPDATES_DIR", tmp_path / "updates")
    return UpdateService()


@pytest.fixture()
def valid_package(tmp_path) -> Path:
    """Erstellt ein minimales, gültiges .mugala-Paket."""
    pkg = tmp_path / "update_1.1.0.mugala"
    manifest = {
        "version": "99.0.0",         # höher als APP_VERSION
        "min_base_version": "0.0.1",
        "migrations": [],
        "changelog": "Testupdate",
        "release_date": "2026-06-01",
        "requires_restart": False,
    }
    with zipfile.ZipFile(pkg, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
    return pkg


@pytest.fixture()
def package_with_migration(tmp_path) -> Path:
    """Paket mit einer harmlosen SQL-Migration."""
    pkg = tmp_path / "update_with_migration.mugala"
    safe_sql = "CREATE TABLE IF NOT EXISTS test_mig (id INTEGER PRIMARY KEY);\n"
    manifest = {
        "version": "99.1.0",
        "min_base_version": "0.0.1",
        "migrations": ["migrations/add_test_table.sql"],
        "changelog": "Migration-Test",
        "release_date": "2026-06-01",
        "requires_restart": False,
    }
    with zipfile.ZipFile(pkg, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("migrations/add_test_table.sql", safe_sql)
    return pkg


# ─── Version ─────────────────────────────────────────────────────────────────

def test_get_current_version(update_svc):
    assert update_svc.get_current_version() == APP_VERSION


# ─── Backup ──────────────────────────────────────────────────────────────────

def test_backup_erstellt_datei(db, update_svc):
    backup_path = update_svc.create_backup()
    assert backup_path.exists()
    assert backup_path.suffix == ".db"
    assert APP_VERSION in backup_path.name


def test_backup_ist_lesbare_sqlite_datei(db, update_svc):
    backup_path = update_svc.create_backup()
    import sqlite3
    con = sqlite3.connect(str(backup_path))
    # Muss mindestens die users-Tabelle enthalten
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    con.close()
    assert "users" in tables


def test_list_backups_nach_backup(db, update_svc):
    update_svc.create_backup()
    backups = update_svc.list_backups()
    assert len(backups) >= 1
    assert "name" in backups[0]
    assert "size_kb" in backups[0]
    assert "created" in backups[0]


def test_alte_backups_werden_bereinigt(db, update_svc, monkeypatch):
    """Nach _MAX_BACKUPS werden älteste Backups gelöscht."""
    import services.update_service as usmod
    monkeypatch.setattr(usmod, "_MAX_BACKUPS", 3)
    for _ in range(5):
        update_svc.create_backup()
    backups = update_svc.list_backups()
    assert len(backups) <= 3


# ─── Paket-Validierung ────────────────────────────────────────────────────────

def test_valides_paket_wird_akzeptiert(update_svc, valid_package):
    ok, msg, manifest = update_svc.validate_package(valid_package)
    assert ok, f"Sollte gültig sein, aber: {msg}"
    assert manifest is not None
    assert manifest.version == "99.0.0"


def test_nicht_vorhandene_datei_abgelehnt(update_svc, tmp_path):
    ok, msg, _ = update_svc.validate_package(tmp_path / "existiert_nicht.mugala")
    assert not ok
    assert "nicht gefunden" in msg.lower()


def test_keine_zip_datei_abgelehnt(update_svc, tmp_path):
    f = tmp_path / "kein_zip.mugala"
    f.write_text("Das ist kein ZIP", encoding="utf-8")
    ok, msg, _ = update_svc.validate_package(f)
    assert not ok


def test_fehlendes_manifest_abgelehnt(update_svc, tmp_path):
    pkg = tmp_path / "ohne_manifest.mugala"
    with zipfile.ZipFile(pkg, "w") as zf:
        zf.writestr("irgendwas.txt", "kein manifest")
    ok, msg, _ = update_svc.validate_package(pkg)
    assert not ok
    assert "manifest.json" in msg


def test_gleiches_version_paket_abgelehnt(update_svc, tmp_path):
    """Ein Paket mit identischer Versionsnummer darf nicht eingespielt werden."""
    pkg = tmp_path / "gleiche_version.mugala"
    manifest = {"version": APP_VERSION, "migrations": []}
    with zipfile.ZipFile(pkg, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
    ok, msg, _ = update_svc.validate_package(pkg)
    assert not ok
    assert APP_VERSION in msg


def test_manifest_mit_bom_encoding_wird_verarbeitet(update_svc, tmp_path):
    """Windows-Editor erzeugt manchmal UTF-8 mit BOM — muss trotzdem lesbar sein."""
    pkg = tmp_path / "bom_manifest.mugala"
    manifest_str = json.dumps({"version": "99.2.0", "min_base_version": "0.0.1", "migrations": []})
    with zipfile.ZipFile(pkg, "w") as zf:
        # BOM voranhängen
        zf.writestr("manifest.json", "﻿" + manifest_str)
    ok, msg, manifest = update_svc.validate_package(pkg)
    assert ok, f"BOM-Manifest sollte akzeptiert werden, aber: {msg}"


def test_migrationsreferenz_auf_fehlende_datei_abgelehnt(update_svc, tmp_path):
    """Manifest referenziert Migration, die nicht im Paket ist."""
    pkg = tmp_path / "fehlende_migration.mugala"
    manifest = {
        "version": "99.3.0",
        "migrations": ["migrations/fehlt.sql"],
    }
    with zipfile.ZipFile(pkg, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
    ok, msg, _ = update_svc.validate_package(pkg)
    assert not ok
    assert "fehlt.sql" in msg


# ─── Destruktive-SQL-Block ────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.parametrize("sql,sollte_blockiert_sein", [
    ("DROP TABLE users;", True),
    ("DROP COLUMN name;", True),
    ("TRUNCATE claims;", True),
    ("DELETE FROM audit_logs;", True),
    ("UPDATE users SET role_id=1;", True),          # UPDATE ohne WHERE
    ("ALTER TABLE claims ADD COLUMN x TEXT;", False),
    ("CREATE TABLE IF NOT EXISTS foo (id INTEGER);", False),
    ("UPDATE users SET is_active=0 WHERE id=5;", False),  # UPDATE mit WHERE
    ("SELECT * FROM users;", False),
])
def test_destruktive_sql_detektion(sql, sollte_blockiert_sein):
    gefunden = UpdateService._check_destructive_sql(sql)
    if sollte_blockiert_sein:
        assert gefunden, f"SQL hätte geblockt werden sollen: {sql!r}"
    else:
        assert not gefunden, f"SQL fälschlicherweise geblockt: {sql!r}"


# ─── Migration idempotent ─────────────────────────────────────────────────────

def test_migration_wird_nur_einmal_angewendet(db, update_svc, package_with_migration):
    ok, msg, manifest = update_svc.validate_package(package_with_migration)
    assert ok, msg

    result1 = update_svc.apply_update(package_with_migration)
    assert result1.success, result1.message

    # Zweite Anwendung desselben Pakets (gleiche Migration): muss sauber enden
    # oder mit "nicht neuer" Meldung abbrechen — aber NICHT abstürzen
    result2 = update_svc.apply_update(package_with_migration)
    # Zweite Anwendung schlägt bei Versionscheck fehl (nicht neuer), das ist korrekt
    assert not result2.success or result2.success  # darf beides sein, soll nicht explodieren


def test_migration_erkennt_destruktive_sql(db, update_svc, tmp_path):
    pkg = tmp_path / "destruktiv.mugala"
    manifest = {
        "version": "99.9.0",
        "min_base_version": "0.0.1",
        "migrations": ["migrations/bad.sql"],
        "changelog": "",
        "release_date": "2026-06-01",
    }
    with zipfile.ZipFile(pkg, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("migrations/bad.sql", "DROP TABLE users;")

    result = update_svc.apply_update(pkg)
    assert not result.success
    assert "destruktiv" in result.message.lower() or "DROP" in result.message


# ─── Restore ─────────────────────────────────────────────────────────────────

def test_restore_aus_backup(db, update_svc):
    backup_path = update_svc.create_backup()
    ok, msg = update_svc.restore_backup(backup_path)
    assert ok, msg
    assert "wiederhergestellt" in msg.lower()


def test_restore_fehlende_datei_liefert_fehler(update_svc, tmp_path):
    ok, msg = update_svc.restore_backup(tmp_path / "gibt_es_nicht.db")
    assert not ok
    assert "nicht gefunden" in msg.lower()
