"""
Software-Update-System für Min Guata Lada.

Update-Pakete sind ZIP-Dateien (Dateiendung .mugala) mit folgender Struktur:
    manifest.json          – Pflichtdatei
    migrations/            – SQL-Migrationsskripte (optional)
        1.1.0_feature.sql
    MinGuataLada-Setup-1.1.0.exe  – Inno-Setup-Installer (optional)

manifest.json-Format:
{
    "version":          "1.1.0",
    "min_base_version": "1.0.0",
    "max_base_version": "1.0.99",
    "installer_file":   "MinGuataLada-Setup-1.1.0.exe",
    "migrations":       ["migrations/1.1.0_feature.sql"],
    "changelog":        "- Neue Funktion\\n- Bugfix",
    "release_date":     "2026-06-01",
    "requires_restart": true
}
"""
import hashlib
import json
import logging
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from app.config import DATA_DIR, DB_PATH, DATABASE_URL

APP_VERSION = "1.3.0"

BACKUPS_DIR = Path(DATA_DIR) / "backups"
UPDATES_DIR = Path(DATA_DIR) / "updates"

_MAX_BACKUPS = 10


class UpdateManifest:
    def __init__(self, data: dict):
        self.version: str = data.get("version", "")
        self.min_base_version: str = data.get("min_base_version", "0.0.0")
        self.max_base_version: str = data.get("max_base_version", "")
        self.installer_file: str = data.get("installer_file", "")
        self.migrations: list[str] = data.get("migrations", [])
        self.changelog: str = data.get("changelog", "")
        self.release_date: str = data.get("release_date", "")
        self.requires_restart: bool = data.get("requires_restart", True)


class UpdateCheckResult:
    def __init__(self, available: bool, version: str = "", url: str = "",
                 sha256: str = "", notes: str = "", error: str = ""):
        self.available = available
        self.version = version
        self.url = url
        self.sha256 = sha256
        self.release_notes = notes
        self.error = error


class UpdateResult:
    def __init__(self, success: bool, message: str = "", backup_path: str = ""):
        self.success = success
        self.message = message
        self.backup_path = backup_path


class UpdateService:
    MANIFEST_URL_SETTING_KEY = "UPDATE_MANIFEST_URL"

    def __init__(self, settings_service=None, audit_service=None):
        self.settings_service = settings_service
        self.audit_service = audit_service
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        UPDATES_DIR.mkdir(parents=True, exist_ok=True)

    # ── Version ────────────────────────────────────────────────────────────

    def get_current_version(self) -> str:
        return APP_VERSION

    def get_manifest_url(self) -> Optional[str]:
        if self.settings_service:
            try:
                url = self.settings_service.get(self.MANIFEST_URL_SETTING_KEY)
                return url if url else None
            except Exception:
                pass
        return None

    # ── Online-Update-Prüfung ──────────────────────────────────────────────

    def check_for_updates(self) -> UpdateCheckResult:
        manifest_url = self.get_manifest_url()
        if not manifest_url:
            return UpdateCheckResult(
                available=False,
                error="Kein Update-Server konfiguriert. Bitte UPDATE_MANIFEST_URL in den Einstellungen setzen.",
            )
        try:
            import urllib.request
            with urllib.request.urlopen(manifest_url, timeout=10) as resp:
                raw = resp.read().decode("utf-8-sig")
            manifest = json.loads(raw)

            # Signatur des Server-Manifests prüfen
            from core.update_signing import verify_package_signature
            sig_ok, sig_msg = verify_package_signature(manifest)
            if not sig_ok:
                return UpdateCheckResult(
                    available=False,
                    error=f"Server-Manifest Signatur ungültig: {sig_msg}",
                )

            remote_version = manifest.get("version", "")
            if self._is_newer(remote_version, APP_VERSION):
                return UpdateCheckResult(
                    available=True,
                    version=remote_version,
                    url=manifest.get("mugala_url", manifest.get("url", "")),
                    sha256=manifest.get("sha256", ""),
                    notes=manifest.get("changelog", ""),
                )
            return UpdateCheckResult(available=False, version=APP_VERSION)
        except Exception as e:
            return UpdateCheckResult(available=False, error=str(e))

    def download_update(self, url: str, expected_sha256: str = "") -> Path:
        """Lädt Update-Paket herunter und prüft optionale SHA-256-Prüfsumme."""
        import urllib.request
        UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        filename = url.split("/")[-1]
        if not filename.endswith((".mugala", ".zip")):
            filename += ".mugala"
        dest = UPDATES_DIR / filename
        urllib.request.urlretrieve(url, dest)
        if expected_sha256:
            actual = hashlib.sha256(dest.read_bytes()).hexdigest()
            if actual.lower() != expected_sha256.lower():
                dest.unlink(missing_ok=True)
                raise ValueError(
                    f"Prüfsumme ungültig.\nErwartet: {expected_sha256}\nErhalten:  {actual}"
                )
        return dest

    # ── Paket-Validierung ──────────────────────────────────────────────────

    def validate_package(self, package_path: Path) -> tuple[bool, str, Optional[UpdateManifest]]:
        """
        Prüft ein Update-Paket auf formale Korrektheit und Kompatibilität.
        Gibt (ok, meldung, manifest) zurück.
        Führt KEINE Datenbankänderungen durch.
        """
        if not package_path.exists():
            return False, "Datei nicht gefunden.", None

        if not zipfile.is_zipfile(package_path):
            return False, "Ungültiges Paketformat. Erwartet wird eine ZIP/.mugala-Datei.", None

        try:
            with zipfile.ZipFile(package_path, "r") as zf:
                names = zf.namelist()

                if "manifest.json" not in names:
                    return False, "manifest.json fehlt im Paket.", None

                try:
                    # utf-8-sig entfernt automatisch ein vorhandenes UTF-8 BOM
                    # (z. B. erzeugt von PowerShell Out-File -Encoding utf8)
                    # und akzeptiert gleichzeitig normales UTF-8 ohne BOM.
                    raw = zf.read("manifest.json").decode("utf-8-sig").strip()
                    manifest_data = json.loads(raw)
                except json.JSONDecodeError as e:
                    return (
                        False,
                        f"manifest.json konnte nicht gelesen werden.\n\n"
                        f"Technischer Fehler: {e}\n\n"
                        f"Mögliche Ursachen:\n"
                        f"  • Datei wurde mit BOM-Encoding gespeichert (z. B. Windows-Editor)\n"
                        f"  • Datei enthält ungültiges JSON (fehlende Anführungszeichen, Kommas)\n"
                        f"  • Datei ist leer oder beschädigt",
                        None,
                    )
                except UnicodeDecodeError as e:
                    return (
                        False,
                        f"manifest.json hat ein unbekanntes Textformat.\n\n"
                        f"Technischer Fehler: {e}\n\n"
                        f"Bitte manifest.json als UTF-8 speichern.",
                        None,
                    )

                # ── Signaturprüfung (Ed25519) ──────────────────────────────
                # Muss VOR der Versionsprüfung erfolgen: ein manipuliertes Paket
                # darf keine weiteren Informationen über seinen Inhalt preisgeben.
                from core.update_signing import verify_package_signature
                sig_ok, sig_msg = verify_package_signature(manifest_data)
                if not sig_ok:
                    return False, sig_msg, None

                manifest = UpdateManifest(manifest_data)

                if not manifest.version:
                    return False, "Manifest enthält keine Versionsnummer.", None

                if not self._is_newer(manifest.version, APP_VERSION):
                    return (
                        False,
                        f"Update-Version {manifest.version} ist nicht neuer als "
                        f"die installierte Version {APP_VERSION}.",
                        None,
                    )

                if manifest.min_base_version:
                    if not self._is_version_gte(APP_VERSION, manifest.min_base_version):
                        return (
                            False,
                            f"Dieses Update erfordert mindestens Version {manifest.min_base_version}. "
                            f"Installiert: {APP_VERSION}.",
                            None,
                        )

                if manifest.max_base_version:
                    if self._is_newer(APP_VERSION, manifest.max_base_version):
                        return (
                            False,
                            f"Dieses Update ist für maximal Version {manifest.max_base_version} "
                            f"geeignet. Installiert: {APP_VERSION}.",
                            None,
                        )

                for migration in manifest.migrations:
                    if migration not in names:
                        return (
                            False,
                            f"Migration '{migration}' im Manifest referenziert, "
                            f"aber nicht im Paket enthalten.",
                            None,
                        )

                if manifest.installer_file and manifest.installer_file not in names:
                    return (
                        False,
                        f"Installer '{manifest.installer_file}' im Manifest referenziert, "
                        f"aber nicht im Paket enthalten.",
                        None,
                    )

                return True, "Paket ist gültig.", manifest

        except Exception as e:
            return False, f"Fehler beim Lesen des Pakets: {e}", None

    # ── Backup ────────────────────────────────────────────────────────────

    def create_backup(self) -> Path:
        """
        Erstellt ein vollständiges Datenbank-Backup.
        PostgreSQL: pg_dump -F c (custom format, komprimiert, restore via pg_restore)
        SQLite:     WAL-Checkpoint + Datei kopieren + PRAGMA integrity_check
        """
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if DATABASE_URL:
            return self._create_postgres_backup(timestamp)
        return self._create_sqlite_backup(timestamp)

    def _create_postgres_backup(self, timestamp: str) -> Path:
        backup_name = f"backup_{timestamp}_v{APP_VERSION}.pgdump"
        backup_path = BACKUPS_DIR / backup_name
        cmd = ["pg_dump", "--format=custom", "--file", str(backup_path), DATABASE_URL]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            msg = f"pg_dump fehlgeschlagen: {result.stderr.strip()}"
            logger.error(msg)
            raise RuntimeError(msg)
        logger.info("PostgreSQL-Backup erstellt: %s", backup_path.name)
        self._cleanup_old_backups()
        return backup_path

    def _create_sqlite_backup(self, timestamp: str) -> Path:
        self._wal_checkpoint()
        backup_name = f"backup_{timestamp}_v{APP_VERSION}.db"
        backup_path = BACKUPS_DIR / backup_name
        shutil.copy2(DB_PATH, backup_path)

        ok, detail = self._verify_backup_integrity(backup_path)
        if not ok:
            backup_path.unlink(missing_ok=True)
            msg = f"Backup-Integritätsprüfung fehlgeschlagen: {detail}"
            logger.error(msg)
            raise RuntimeError(msg)

        logger.info("Backup erstellt und verifiziert: %s", backup_path.name)
        self._cleanup_old_backups()
        return backup_path

    def _verify_backup_integrity(self, backup_path: Path) -> tuple[bool, str]:
        """PRAGMA integrity_check auf einer SQLite-Backup-Kopie."""
        if not backup_path.exists():
            return False, f"Datei nicht gefunden: {backup_path.name}"

        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(str(backup_path))
            try:
                rows = conn.execute("PRAGMA integrity_check").fetchall()
            finally:
                conn.close()
                conn = None
            results = [r[0] for r in rows]
            if results == ["ok"]:
                return True, "ok"
            detail = "; ".join(results[:5])
            logger.error("Backup-Integritätsfehler in '%s': %s", backup_path.name, detail)
            return False, detail
        except Exception as exc:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            logger.error("Backup-Integritätsprüfung: Ausnahme für '%s': %s", backup_path.name, exc)
            return False, str(exc)

    def _wal_checkpoint(self) -> None:
        """WAL-Checkpoint vor SQLite-Backup für Datenkonsistenz."""
        try:
            from database.db import get_connection
            with get_connection() as conn:
                conn.execute("PRAGMA wal_checkpoint(FULL)")
        except Exception:
            pass

    def _cleanup_old_backups(self) -> None:
        for pattern in ("backup_*.db", "backup_*.pgdump"):
            backups = sorted(
                BACKUPS_DIR.glob(pattern),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for old in backups[_MAX_BACKUPS:]:
                try:
                    old.unlink()
                except Exception:
                    pass

    def list_backups(self) -> list[dict]:
        backups = sorted(
            [*BACKUPS_DIR.glob("backup_*.db"), *BACKUPS_DIR.glob("backup_*.pgdump")],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        result = []
        for bp in backups:
            stat = bp.stat()
            result.append({
                "path": str(bp),
                "name": bp.name,
                "size_kb": round(stat.st_size / 1024, 1),
                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M:%S"),
            })
        return result

    # ── Wiederherstellung ──────────────────────────────────────────────────

    def restore_backup(self, backup_path: Path) -> tuple[bool, str]:
        """
        Stellt die Datenbank aus einem Backup wieder her.
        PostgreSQL: pg_restore — ACHTUNG: überschreibt alle Daten!
        SQLite:     Datei-Kopie + Neustart erforderlich.
        """
        if not backup_path.exists():
            return False, f"Backup-Datei nicht gefunden: {backup_path}"

        if DATABASE_URL and backup_path.suffix == ".pgdump":
            return self._restore_postgres_backup(backup_path)
        return self._restore_sqlite_backup(backup_path)

    def _restore_postgres_backup(self, backup_path: Path) -> tuple[bool, str]:
        try:
            safety_path = self._create_postgres_backup(
                datetime.now().strftime("pre_restore_%Y%m%d_%H%M%S")
            )
            cmd = ["pg_restore", "--clean", "--if-exists", "--dbname", DATABASE_URL, str(backup_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return False, f"pg_restore fehlgeschlagen: {result.stderr.strip()}"
            self._log_audit(
                action="BACKUP_RESTORED",
                details=f"PostgreSQL-Datenbank aus '{backup_path.name}' wiederhergestellt.",
            )
            return True, (
                f"Datenbank aus '{backup_path.name}' wiederhergestellt.\n"
                f"Sicherheits-Backup: {safety_path.name}\n\n"
                "Die Anwendung muss jetzt neu gestartet werden."
            )
        except Exception as e:
            return False, f"Wiederherstellung fehlgeschlagen: {e}"

    def _restore_sqlite_backup(self, backup_path: Path) -> tuple[bool, str]:
        try:
            self._wal_checkpoint()
            safety_name = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(DB_PATH, BACKUPS_DIR / safety_name)
            shutil.copy2(backup_path, DB_PATH)
            self._log_audit(
                action="BACKUP_RESTORED",
                details=f"Datenbank aus Backup '{backup_path.name}' wiederhergestellt.",
            )
            return True, (
                f"Datenbank aus '{backup_path.name}' wiederhergestellt.\n"
                f"Sicherheits-Backup des vorherigen Zustands: {safety_name}\n\n"
                "Die Anwendung muss jetzt neu gestartet werden."
            )
        except Exception as e:
            return False, f"Wiederherstellung fehlgeschlagen: {e}"

    # ── Update einspielen ──────────────────────────────────────────────────

    def apply_update(self, package_path: Path, user_id: int = None) -> UpdateResult:
        """
        Vollständiger, sicherer Update-Ablauf:
          1. Paket validieren
          2. Datenbank-Backup erstellen
          3. Migrationen ausführen (idempotent, additive)
          4. Update in update_history protokollieren
          5. Installer starten (falls enthalten) und Anwendung beenden
        """
        # Schritt 1: Validierung
        ok, msg, manifest = self.validate_package(package_path)
        if not ok:
            self._record_failure(version=None, error=msg, user_id=user_id)
            return UpdateResult(success=False, message=f"Validierung fehlgeschlagen:\n{msg}")

        # Schritt 2: Backup
        try:
            backup_path = self.create_backup()
        except Exception as e:
            err = f"Backup konnte nicht erstellt werden: {e}"
            self._record_failure(version=manifest.version, error=err, user_id=user_id)
            return UpdateResult(success=False, message=err)

        # Schritt 3 & 4: Paket entpacken, Migrationen ausführen
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            try:
                with zipfile.ZipFile(package_path, "r") as zf:
                    zf.extractall(tmp)
            except Exception as e:
                err = f"Paket konnte nicht entpackt werden: {e}"
                self._record_failure(manifest.version, err, user_id)
                return UpdateResult(
                    success=False,
                    message=err + f"\n\nBackup gesichert unter:\n{backup_path}",
                    backup_path=str(backup_path),
                )

            applied_migrations: list[str] = []
            for migration_file in manifest.migrations:
                migration_path = tmp / migration_file
                ok, err = self._apply_migration(migration_path, manifest.version)
                if not ok:
                    msg = f"Migration '{migration_file}' fehlgeschlagen:\n{err}"
                    self._record_failure(manifest.version, msg, user_id)
                    return UpdateResult(
                        success=False,
                        message=(
                            msg
                            + f"\n\nDie Datenbank wurde NICHT verändert, sofern die Migration "
                            f"atomar fehlgeschlagen ist.\n"
                            f"Backup verfügbar unter:\n{backup_path}"
                        ),
                        backup_path=str(backup_path),
                    )
                applied_migrations.append(migration_file)

            # Schritt 4: Erfolg protokollieren
            self._record_success(
                version=manifest.version,
                changelog=manifest.changelog,
                backup_path=str(backup_path),
                migrations=applied_migrations,
                user_id=user_id,
            )

            # Schritt 5: Installer starten (falls vorhanden)
            if manifest.installer_file:
                installer_src = tmp / manifest.installer_file
                if installer_src.exists():
                    # Alle extrahierten Dateien (ausser manifest.json) nach UPDATES_DIR kopieren,
                    # damit _internal/ neben der EXE liegt und die DLLs gefunden werden.
                    for item in tmp.iterdir():
                        if item.name == "manifest.json":
                            continue
                        dest = UPDATES_DIR / item.name
                        try:
                            if item.is_dir():
                                if dest.exists():
                                    shutil.rmtree(dest)
                                shutil.copytree(item, dest)
                            else:
                                shutil.copy2(item, dest)
                        except Exception:
                            pass

                    perm_installer = UPDATES_DIR / manifest.installer_file
                    try:
                        # Aktuelles Installationsverzeichnis ermitteln, damit die neue EXE
                        # sich nach dem Start selbst dorthin kopiert (Self-Replacement).
                        # Das stellt sicher, dass Desktop-Shortcuts nach dem Update weiterhin
                        # auf die richtige EXE zeigen.
                        import sys as _sys
                        launch_args = [str(perm_installer)]
                        if getattr(_sys, "frozen", False):
                            current_install_dir = Path(_sys.executable).parent.resolve()
                            if current_install_dir != UPDATES_DIR.resolve():
                                launch_args += ["--mgl-replace", str(current_install_dir)]

                        subprocess.Popen(
                            launch_args,
                            creationflags=subprocess.DETACHED_PROCESS,
                        )
                        _sys.exit(0)
                    except Exception as e:
                        return UpdateResult(
                            success=True,
                            message=(
                                f"Migrationen erfolgreich auf Version {manifest.version}.\n\n"
                                f"Neustart konnte nicht automatisch ausgeführt werden:\n{e}\n\n"
                                f"Bitte die Anwendung manuell neu starten:\n{perm_installer}"
                            ),
                            backup_path=str(backup_path),
                        )

        return UpdateResult(
            success=True,
            message=(
                f"Update auf Version {manifest.version} erfolgreich eingespielt.\n"
                f"Angewendete Migrationen: {len(applied_migrations)}\n"
                f"Backup: {backup_path}"
            ),
            backup_path=str(backup_path),
        )

    # ── Migration ─────────────────────────────────────────────────────────

    def _apply_migration(self, migration_path: Path, version: str) -> tuple[bool, str]:
        """
        Führt eine einzelne SQL-Migrationsdatei idempotent aus.
        Migrationen werden nur einmalig angewendet (Prüfung via update_migrations-Tabelle).
        Nur additive SQL-Operationen (ALTER TABLE ADD COLUMN, CREATE TABLE IF NOT EXISTS)
        sind erlaubt. Destruktive Operationen (DROP, DELETE ohne WHERE) führen zu einem Fehler.
        """
        try:
            sql = migration_path.read_text(encoding="utf-8")

            # Sicherheitsprüfung: destruktive Operationen blockieren
            blocked = self._check_destructive_sql(sql)
            if blocked:
                return False, (
                    f"Migration enthält potenziell destruktive SQL-Anweisung: '{blocked}'. "
                    "Update abgebrochen. Bitte Migrationsskript prüfen."
                )

            from database.db import get_connection
            with get_connection() as conn:
                self._ensure_update_tables(conn)

                already_applied = conn.execute(
                    "SELECT id FROM update_migrations WHERE migration_file = ?",
                    (migration_path.name,),
                ).fetchone()
                if already_applied:
                    return True, ""

                conn.executescript(sql)

                conn.execute(
                    "INSERT INTO update_migrations (version, migration_file, applied_at) "
                    "VALUES (?, ?, ?)",
                    (version, migration_path.name, datetime.now().isoformat()),
                )
                conn.commit()

            return True, ""
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _check_destructive_sql(sql: str) -> str:
        """
        Einfache Prüfung auf destruktive SQL-Anweisungen.
        Gibt den gefundenen blockierten Begriff zurück, sonst leeren String.
        """
        import re
        normalized = sql.upper()
        patterns = [
            r"\bDROP\s+TABLE\b",
            r"\bDROP\s+COLUMN\b",
            r"\bTRUNCATE\b",
            r"\bDELETE\s+FROM\s+\w+\s*;",    # DELETE ohne WHERE
            r"\bUPDATE\s+\w+\s+SET\b(?!.*\bWHERE\b)",  # UPDATE ohne WHERE
        ]
        for pat in patterns:
            if re.search(pat, normalized):
                match = re.search(pat, normalized)
                return match.group(0).strip() if match else pat
        return ""

    @staticmethod
    def _ensure_update_tables(conn) -> None:
        """Stellt sicher, dass die Update-Tracking-Tabellen existieren (Safety-Net)."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS update_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'SUCCESS',
                changelog TEXT,
                backup_path TEXT,
                applied_migrations TEXT,
                error_message TEXT,
                applied_by INTEGER,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS update_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                migration_file TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # ── Update-Verlauf ─────────────────────────────────────────────────────

    def get_update_history(self) -> list[dict]:
        try:
            from database.db import get_connection
            with get_connection() as conn:
                self._ensure_update_tables(conn)
                rows = conn.execute(
                    "SELECT * FROM update_history ORDER BY applied_at DESC LIMIT 100"
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def get_applied_migrations(self) -> list[dict]:
        try:
            from database.db import get_connection
            with get_connection() as conn:
                self._ensure_update_tables(conn)
                rows = conn.execute(
                    "SELECT * FROM update_migrations ORDER BY applied_at DESC"
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def get_last_successful_update(self) -> Optional[dict]:
        try:
            from database.db import get_connection
            with get_connection() as conn:
                self._ensure_update_tables(conn)
                row = conn.execute(
                    "SELECT * FROM update_history WHERE status = 'SUCCESS' "
                    "ORDER BY applied_at DESC LIMIT 1"
                ).fetchone()
                return dict(row) if row else None
        except Exception:
            return None

    # ── Protokollierung ────────────────────────────────────────────────────

    def _record_success(self, version: str, changelog: str, backup_path: str,
                        migrations: list[str], user_id: int = None) -> None:
        try:
            from database.db import get_connection
            with get_connection() as conn:
                self._ensure_update_tables(conn)
                conn.execute(
                    """INSERT INTO update_history
                       (version, status, changelog, backup_path, applied_migrations,
                        applied_by, applied_at)
                       VALUES (?, 'SUCCESS', ?, ?, ?, ?, ?)""",
                    (
                        version, changelog, backup_path,
                        json.dumps(migrations), user_id,
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
        except Exception:
            pass
        self._log_audit(
            action="UPDATE_APPLIED",
            details=f"Update auf Version {version} erfolgreich. Migrationen: {len(migrations)}. Backup: {backup_path}",
            user_id=user_id,
        )

    def _record_failure(self, version: Optional[str], error: str, user_id: int = None) -> None:
        try:
            from database.db import get_connection
            with get_connection() as conn:
                self._ensure_update_tables(conn)
                conn.execute(
                    """INSERT INTO update_history
                       (version, status, changelog, backup_path, applied_migrations,
                        error_message, applied_by, applied_at)
                       VALUES (?, 'FAILED', '', '', '[]', ?, ?, ?)""",
                    (
                        version or "unbekannt",
                        error[:2000],
                        user_id,
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
        except Exception:
            pass
        self._log_audit(
            action="UPDATE_FAILED",
            details=f"Update fehlgeschlagen (Version {version or 'unbekannt'}): {error[:500]}",
            user_id=user_id,
        )

    def _log_audit(self, action: str, details: str, user_id: int = None) -> None:
        if self.audit_service:
            try:
                self.audit_service.log(
                    user_id=user_id,
                    action=action,
                    object_type="system",
                    object_id=None,
                    details=details,
                )
            except Exception:
                pass

    # ── Hilfsmethoden ──────────────────────────────────────────────────────

    @staticmethod
    def _is_newer(remote: str, local: str) -> bool:
        try:
            r = tuple(int(x) for x in remote.strip().split("."))
            l = tuple(int(x) for x in local.strip().split("."))
            return r > l
        except Exception:
            return False

    @staticmethod
    def _is_version_gte(version: str, minimum: str) -> bool:
        try:
            v = tuple(int(x) for x in version.strip().split("."))
            m = tuple(int(x) for x in minimum.strip().split("."))
            return v >= m
        except Exception:
            return True
