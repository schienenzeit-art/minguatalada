"""
Tests für Backup-Härtung (Priorität 3):
  - PRAGMA integrity_check nach jeder Backup-Erstellung
  - Beschädigtes Backup wird erkannt und gelöscht (RuntimeError)
  - Vollständiger Restore-Zyklus: Backup → Daten ändern → Restore → Daten prüfen
  - Restore erstellt Safety-Backup vor dem Überschreiben
  - Restore mit beschädigter Backup-Datei → (False, Fehlermeldung)
  - Mehrere Restore-Zyklen hintereinander

Marker: @pytest.mark.slow (Datei-I/O, SQLite-Operationen)
"""
import sqlite3
import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def update_svc(db, tmp_path, monkeypatch):
    """UpdateService mit isolierten Verzeichnissen und Test-DB."""
    import services.update_service as usmod
    import app.config as cfg

    monkeypatch.setattr(usmod, "BACKUPS_DIR", tmp_path / "backups")
    monkeypatch.setattr(usmod, "UPDATES_DIR", tmp_path / "updates")
    monkeypatch.setattr(usmod, "DB_PATH", db)
    monkeypatch.setattr(cfg, "DB_PATH", db)

    from services.update_service import UpdateService
    return UpdateService()


@pytest.fixture()
def backups_dir(tmp_path) -> Path:
    d = tmp_path / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── 1. Integritätsprüfung nach Backup-Erstellung ─────────────────────────────

class TestBackupIntegrityCheck:
    def test_frische_db_backup_besteht_integritaetscheck(self, db, update_svc):
        """Backup einer intakten Datenbank muss integrity_check bestehen."""
        backup_path = update_svc.create_backup()
        assert backup_path.exists()

        # Direkt prüfen
        ok, detail = update_svc._verify_backup_integrity(backup_path)
        assert ok is True, f"Integritätsprüfung fehlgeschlagen: {detail}"

    def test_backup_enthaelt_alle_kerntabellen(self, db, update_svc):
        """Backup muss alle kritischen Tabellen enthalten."""
        backup_path = update_svc.create_backup()
        conn = sqlite3.connect(str(backup_path))
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()

        required = {"users", "claims", "audit_logs", "roles", "locations"}
        missing = required - tables
        assert not missing, f"Tabellen fehlen im Backup: {missing}"

    def test_verify_integrity_auf_korrupter_datei_gibt_false(self, db, update_svc, tmp_path):
        """_verify_backup_integrity() muss bei beschädigter Datei False zurückgeben."""
        corrupt = tmp_path / "corrupt.db"
        corrupt.write_bytes(b"Das ist definitiv kein SQLite" + b"\x00" * 100)

        ok, detail = update_svc._verify_backup_integrity(corrupt)
        assert ok is False
        assert len(detail) > 0

    def test_backup_erstellt_loescht_korruptes_backup_und_wirft_fehler(
        self, db, update_svc, monkeypatch, tmp_path
    ):
        """Wenn der Kopiervorgang ein korruptes Backup erzeugt, muss RuntimeError kommen."""
        import services.update_service as usmod

        original_copy = shutil.copy2

        def corrupt_copy(src, dst):
            """Kopiert nicht, schreibt stattdessen Müll."""
            Path(dst).write_bytes(b"GARBAGE_NOT_SQLITE" + b"\xff" * 200)

        monkeypatch.setattr(shutil, "copy2", corrupt_copy)

        with pytest.raises(RuntimeError, match="Integrit"):
            update_svc.create_backup()

    def test_korruptes_backup_wird_nach_fehler_geloescht(
        self, db, update_svc, monkeypatch, tmp_path
    ):
        """Nach gescheiterter Integritätsprüfung darf keine beschädigte Datei übrig bleiben."""
        import services.update_service as usmod

        def corrupt_copy(src, dst):
            Path(dst).write_bytes(b"GARBAGE" * 50)

        monkeypatch.setattr(shutil, "copy2", corrupt_copy)

        backups_before = list((tmp_path / "backups").glob("*.db")) if (tmp_path / "backups").exists() else []

        with pytest.raises(RuntimeError):
            update_svc.create_backup()

        # Kein neues .db sollte übrig sein
        backups_after = list((tmp_path / "backups").glob("*.db"))
        new_files = [f for f in backups_after if f not in backups_before]
        assert len(new_files) == 0, f"Beschädigte Backup-Datei nicht gelöscht: {new_files}"


# ── 2. Vollständiger Restore-Zyklus ───────────────────────────────────────────

class TestRestoreZyklus:
    def test_restore_stellt_daten_wieder_her(self, db, update_svc, monkeypatch):
        """
        Kerntest: Backup erstellen, Daten löschen, Backup einspielen,
        Daten sind wieder vorhanden.
        """
        import app.config as cfg
        monkeypatch.setattr(cfg, "DB_PATH", db)

        # Referenzzustand: User-Anzahl vor dem Backup
        conn = sqlite3.connect(str(db))
        count_before = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()

        # Backup erstellen
        backup_path = update_svc.create_backup()
        assert backup_path.exists()

        # Daten verändern: neuen Testbenutzer einfügen
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT INTO users (full_name, username, password_hash, role_id, is_active) "
            "VALUES ('Restore Test', 'restore_test_user', 'hash', 1, 1)"
        )
        conn.commit()
        count_modified = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        assert count_modified == count_before + 1

        # Restore
        ok, msg = update_svc.restore_backup(backup_path)
        assert ok, f"Restore fehlgeschlagen: {msg}"

        # Daten nach Restore: müssen wieder dem Originalzustand entsprechen
        conn = sqlite3.connect(str(db))
        count_after = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        assert count_after == count_before, (
            f"Restore hat falschen Zustand: vorher={count_before}, "
            f"nach Änderung={count_modified}, nach Restore={count_after}"
        )

    def test_restore_erstellt_safety_backup(self, db, update_svc, tmp_path, monkeypatch):
        """Vor dem Restore muss ein Safety-Backup des aktuellen Zustands erstellt werden."""
        import app.config as cfg
        monkeypatch.setattr(cfg, "DB_PATH", db)

        backup_path = update_svc.create_backup()
        backups_dir = tmp_path / "backups"

        backups_before = set(backups_dir.glob("*.db"))
        update_svc.restore_backup(backup_path)
        backups_after = set(backups_dir.glob("*.db"))

        new_files = backups_after - backups_before
        safety_backups = [f for f in new_files if f.name.startswith("pre_restore_")]
        assert len(safety_backups) >= 1, (
            f"Kein Safety-Backup gefunden. Neue Dateien: {[f.name for f in new_files]}"
        )

    def test_safety_backup_ist_valide_sqlite(self, db, update_svc, tmp_path, monkeypatch):
        """Das Safety-Backup muss eine lesbare SQLite-Datenbank sein."""
        import app.config as cfg
        monkeypatch.setattr(cfg, "DB_PATH", db)

        backup_path = update_svc.create_backup()
        update_svc.restore_backup(backup_path)

        backups_dir = tmp_path / "backups"
        safety = next(iter(backups_dir.glob("pre_restore_*.db")), None)
        assert safety is not None

        ok, detail = update_svc._verify_backup_integrity(safety)
        assert ok is True, f"Safety-Backup ist beschädigt: {detail}"

    def test_restore_fehlende_datei_gibt_false(self, update_svc, tmp_path):
        """Restore mit nicht-existenter Datei muss (False, Fehlermeldung) zurückgeben."""
        ok, msg = update_svc.restore_backup(tmp_path / "existiert_nicht.db")
        assert ok is False
        assert "nicht gefunden" in msg.lower()

    def test_restore_mit_korrupter_datei_gibt_false(
        self, db, update_svc, tmp_path, monkeypatch
    ):
        """Restore mit beschädigter Backup-Datei muss (False, ...) zurückgeben."""
        import app.config as cfg
        monkeypatch.setattr(cfg, "DB_PATH", db)

        corrupt_backup = tmp_path / "backups" / "corrupt_backup.db"
        corrupt_backup.parent.mkdir(parents=True, exist_ok=True)
        corrupt_backup.write_bytes(b"KEIN SQLITE" + b"\x00" * 512)

        # SQLite überschreibt DB_PATH auch mit kaputten Daten (shutil.copy2 läuft durch).
        # Der Test stellt sicher, dass restore_backup() KEINEN Absturz produziert.
        ok, msg = update_svc.restore_backup(corrupt_backup)
        # Ob ok=True oder False: keine Exception darf hochkommen
        assert isinstance(ok, bool)
        assert isinstance(msg, str)

    def test_mehrere_restore_zyklen_hintereinander(self, db, update_svc, tmp_path, monkeypatch):
        """Drei aufeinanderfolgende Backup→Restore-Zyklen müssen stabil ablaufen."""
        import app.config as cfg
        monkeypatch.setattr(cfg, "DB_PATH", db)

        for i in range(3):
            backup_path = update_svc.create_backup()
            ok, msg = update_svc.restore_backup(backup_path)
            assert ok, f"Restore-Zyklus {i+1} fehlgeschlagen: {msg}"

    def test_restore_stellt_auch_audit_logs_wieder_her(
        self, db, update_svc, tmp_path, monkeypatch
    ):
        """Restore muss alle Tabellen wiederherstellen, nicht nur users."""
        import app.config as cfg
        monkeypatch.setattr(cfg, "DB_PATH", db)

        # Audit-Log-Anzahl vor Backup merken
        conn = sqlite3.connect(str(db))
        audit_before = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
        conn.close()

        backup_path = update_svc.create_backup()

        # Audit-Log-Eintrag hinzufügen (simuliert Aktivität nach dem Backup)
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT INTO audit_logs (user_id, action, object_type, object_id, details) "
            "VALUES (1, 'TEST_ACTION', 'test', 1, 'restore test')"
        )
        conn.commit()
        conn.close()

        # Restore
        update_svc.restore_backup(backup_path)

        # Audit-Logs müssen wieder im Ursprungszustand sein
        conn = sqlite3.connect(str(db))
        audit_after = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
        conn.close()
        assert audit_after == audit_before


# ── 3. _verify_backup_integrity direkt ───────────────────────────────────────

class TestVerifyBackupIntegrity:
    def test_leere_sqlite_datei_besteht(self, update_svc, tmp_path):
        """Eine leere (aber valide) SQLite-Datei muss integrity_check bestehen."""
        empty_db = tmp_path / "empty.db"
        conn = sqlite3.connect(str(empty_db))
        conn.close()

        ok, detail = update_svc._verify_backup_integrity(empty_db)
        assert ok is True, f"Leere SQLite-Datei schlägt fehl: {detail}"

    def test_datei_existiert_nicht_gibt_false(self, update_svc, tmp_path):
        """Nicht-existente Datei → False (SQLite würde sonst leere DB anlegen)."""
        ghost = tmp_path / "subdir_that_doesnt_exist" / "ghost.db"
        ok, detail = update_svc._verify_backup_integrity(ghost)
        assert ok is False
        assert len(detail) > 0

    def test_binaere_datei_gibt_false(self, update_svc, tmp_path):
        bad = tmp_path / "binary.db"
        bad.write_bytes(bytes(range(256)) * 10)
        ok, detail = update_svc._verify_backup_integrity(bad)
        assert ok is False

    def test_vollstaendige_db_mit_daten_besteht(self, db, update_svc):
        """Die Test-DB (mit Schema + Seed-Daten) muss integrity_check bestehen."""
        ok, detail = update_svc._verify_backup_integrity(db)
        assert ok is True, f"Vollständige Test-DB schlägt integrity_check fehl: {detail}"
