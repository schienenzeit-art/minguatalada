import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, UTC
from pathlib import Path
from typing import Generator

from app.config import DATA_DIR, DB_PATH, DATABASE_URL
from core.claim_status import ClaimStatus
from database.seed import seed_basic_data

logger = logging.getLogger(__name__)

# ── Backend detection ─────────────────────────────────────────────────────────

IS_POSTGRES: bool = bool(DATABASE_URL)

# ── PostgreSQL connection pool (lazy init) ───────────────────────────────────

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        try:
            import psycopg
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool

            def _configure(conn):
                conn.row_factory = dict_row

            _pool = ConnectionPool(
                conninfo=DATABASE_URL,
                min_size=1,
                max_size=10,
                configure=_configure,
                open=True,
            )
            logger.info("PostgreSQL-Verbindungspool geöffnet (%s)", DATABASE_URL.split('@')[-1])
        except Exception as exc:
            logger.critical("PostgreSQL-Pool konnte nicht erstellt werden: %s", exc)
            raise
    return _pool


# ── get_connection() ──────────────────────────────────────────────────────────

@contextmanager
def get_connection() -> Generator:
    """
    Context manager that yields a database connection.
    - PostgreSQL: yields PgConnectionAdapter wrapping a pool connection.
    - SQLite:     yields sqlite3.Connection (unchanged legacy behaviour).
    All repositories use `with get_connection() as conn:` without modification.
    """
    if IS_POSTGRES:
        from database.connection_adapter import PgConnectionAdapter
        pool = _get_pool()
        with pool.connection() as pg_conn:
            yield PgConnectionAdapter(pg_conn)
    else:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()


# ── Health check ──────────────────────────────────────────────────────────────

def check_database_health() -> tuple[bool, list[str]]:
    """
    Prüft beim Start ob die Datenbank erreichbar, konsistent und korrekt
    konfiguriert ist. Gibt (ok, meldungen) zurück.
    """
    messages: list[str] = []
    try:
        if IS_POSTGRES:
            with get_connection() as conn:
                conn.execute("SELECT 1")
            logger.info("Healthcheck OK — PostgreSQL erreichbar.")
            return True, []

        # SQLite-Prüfungen
        with get_connection() as conn:
            fk_row = conn.execute("PRAGMA foreign_keys").fetchone()
            if not fk_row or fk_row[0] != 1:
                msg = "PRAGMA foreign_keys ist nicht aktiv."
                messages.append(msg)
                logger.warning("Healthcheck: %s", msg)

            jm_row = conn.execute("PRAGMA journal_mode").fetchone()
            if jm_row and jm_row[0].lower() != "wal":
                msg = f"Journal-Modus ist '{jm_row[0]}', erwartet 'wal'."
                messages.append(msg)
                logger.warning("Healthcheck: %s", msg)

            rows = conn.execute("PRAGMA integrity_check").fetchall()
            results = [r[0] for r in rows]
            if results != ["ok"]:
                detail = "; ".join(results[:5])
                msg = f"Integritätsfehler: {detail}"
                messages.append(msg)
                logger.error("Healthcheck: %s", msg)
                return False, messages

    except Exception as exc:
        msg = f"Datenbank nicht erreichbar: {exc}"
        messages.append(msg)
        logger.critical("Healthcheck fehlgeschlagen: %s", exc)
        return False, messages

    if not any(m.startswith("Integrit") for m in messages):
        logger.info("Healthcheck OK — WAL, FK, Integrität geprüft.")

    critical = [m for m in messages if "Integrit" in m or "nicht erreichbar" in m]
    return len(critical) == 0, messages


# ── Database initialisation ───────────────────────────────────────────────────

def ensure_data_dir() -> None:
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def initialize_database() -> None:
    if IS_POSTGRES:
        _initialize_postgres()
    else:
        _initialize_sqlite()


def _initialize_postgres() -> None:
    """Apply the full PostgreSQL schema (idempotent) and seed basic data."""
    schema_path = Path(__file__).parent / "schema_postgres.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    with get_connection() as conn:
        # Execute schema (CREATE TABLE IF NOT EXISTS + seed INSERTs)
        for stmt in schema_sql.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                conn.execute(stmt)
        conn.commit()

    # Mark all SQLite migrations as applied so run_migrations() is a no-op
    from database.migrations import MIGRATIONS
    with get_connection() as conn:
        for version, description in MIGRATIONS:
            conn.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (%s, %s)"
                " ON CONFLICT (version) DO NOTHING",
                (version, description),
            )
        conn.commit()

    # Seed users / roles / settings (idempotent)
    with get_connection() as conn:
        seed_basic_data(conn)
        conn.commit()

    logger.info("PostgreSQL-Datenbank initialisiert.")


def _initialize_sqlite() -> None:
    """Legacy SQLite initialisation (unchanged)."""
    ensure_data_dir()

    from database.migrations import run_migrations

    with get_connection() as connection:
        result = connection.execute("PRAGMA journal_mode=WAL").fetchone()
        if result and result[0].lower() == "wal":
            logger.debug("WAL-Modus aktiv.")
        else:
            logger.warning(
                "WAL-Modus konnte nicht aktiviert werden (journal_mode=%s).",
                result[0] if result else "?",
            )

        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                location_id INTEGER,
                is_active INTEGER NOT NULL DEFAULT 1,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (role_id) REFERENCES roles(id),
                FOREIGN KEY (location_id) REFERENCES locations(id)
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                value_type TEXT NOT NULL,
                category TEXT,
                description TEXT,
                editable_by_admin INTEGER NOT NULL DEFAULT 1,
                updated_by INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                address TEXT NOT NULL,
                postal_code TEXT NOT NULL,
                city TEXT NOT NULL,
                email TEXT,
                category_id INTEGER,
                location_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (location_id) REFERENCES locations(id)
            );

            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT NOT NULL UNIQUE,
                person_id INTEGER,
                user_id INTEGER NOT NULL,
                location_id INTEGER NOT NULL,
                category_id INTEGER,
                status TEXT NOT NULL,
                description TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                review_date TEXT,
                created_by INTEGER,
                examiner_id INTEGER,
                evaluation_date TEXT,
                adult_count INTEGER DEFAULT 1,
                child_count INTEGER DEFAULT 0,
                disability_degree INTEGER,
                evaluation_reason TEXT,
                total_income REAL,
                total_expenses REAL,
                free_income REAL,
                entitlement_limit REAL,
                hardship_limit REAL,
                evaluation_details TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (person_id) REFERENCES persons(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (location_id) REFERENCES locations(id),
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (created_by) REFERENCES users(id),
                FOREIGN KEY (examiner_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS claim_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                changed_by INTEGER,
                changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                old_status TEXT,
                new_status TEXT NOT NULL,
                note TEXT,
                FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
                FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS incomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                note TEXT,
                FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                has_proof INTEGER NOT NULL DEFAULT 0,
                note TEXT,
                FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_number TEXT NOT NULL UNIQUE,
                claim_id INTEGER NOT NULL,
                person_id INTEGER NOT NULL,
                location_id INTEGER NOT NULL,
                issue_date TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'AKTIV',
                note TEXT,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
                FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE,
                FOREIGN KEY (location_id) REFERENCES locations(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS document_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                original_file_name TEXT NOT NULL,
                file_name TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                document_type_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                description TEXT,
                claim_id INTEGER,
                person_id INTEGER,
                card_id INTEGER,
                location_id INTEGER,
                uploaded_by INTEGER,
                uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                archived_at TEXT,
                expiry_date TEXT,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (document_type_id) REFERENCES document_types(id),
                FOREIGN KEY (claim_id) REFERENCES claims(id),
                FOREIGN KEY (person_id) REFERENCES persons(id),
                FOREIGN KEY (card_id) REFERENCES cards(id),
                FOREIGN KEY (location_id) REFERENCES locations(id),
                FOREIGN KEY (uploaded_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                task_type TEXT,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                due_date TEXT,
                assigned_user_id INTEGER,
                location_id INTEGER,
                source_type TEXT,
                source_ref_type TEXT,
                source_ref_id INTEGER,
                source_description TEXT,
                is_system_task INTEGER NOT NULL DEFAULT 0,
                created_by INTEGER,
                completed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assigned_user_id) REFERENCES users(id),
                FOREIGN KEY (location_id) REFERENCES locations(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                action TEXT NOT NULL,
                object_type TEXT NOT NULL,
                object_id INTEGER,
                details TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS claim_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                user_id INTEGER,
                note_text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS filter_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                filter_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        migrate_existing_claim_statuses(connection)
        from database.migrations import run_migrations
        run_migrations(connection)
        seed_basic_data(connection)

        # Fallback: Aktenzeichen für bestehende Anträge ohne case_number vergeben
        try:
            rows = connection.execute("SELECT id, case_number FROM claims ORDER BY id").fetchall()
            year = datetime.now(UTC).year
            for row in rows:
                if not row["case_number"]:
                    last = connection.execute(
                        "SELECT case_number FROM claims WHERE case_number LIKE ? ORDER BY case_number DESC LIMIT 1",
                        (f"AS-{year}-%",),
                    ).fetchone()
                    if last and last["case_number"]:
                        try:
                            seq = int(last["case_number"].split("-")[-1]) + 1
                        except Exception:
                            seq = 1
                    else:
                        seq = 1
                    connection.execute(
                        "UPDATE claims SET case_number = ? WHERE id = ?",
                        (f"AS-{year}-{seq:06d}", row["id"]),
                    )
            connection.commit()
        except Exception:
            pass


def migrate_existing_claim_statuses(connection) -> None:
    mapping = {
        "Entwurf": ClaimStatus.IN_PRUEFUNG,
        "Eingereicht": ClaimStatus.IN_PRUEFUNG,
        "In Prüfung": ClaimStatus.IN_PRUEFUNG,
        "Genehmigt": ClaimStatus.ANSPRUCHSBERECHTIGT,
        "Abgelehnt": ClaimStatus.ABGELEHNT,
        "Erledigt": ClaimStatus.ARCHIVIERT,
    }
    for old_status, new_status in mapping.items():
        connection.execute(
            "UPDATE claims SET status = ? WHERE status = ?",
            (new_status, old_status),
        )
    connection.commit()


def is_database_ready() -> bool:
    try:
        if not IS_POSTGRES:
            ensure_data_dir()
        with get_connection() as connection:
            connection.execute("SELECT 1")
        return True
    except Exception:
        return False
