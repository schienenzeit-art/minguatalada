import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, UTC

from app.config import DATA_DIR, DB_PATH
from core.claim_status import ClaimStatus
from services.password_service import PasswordService
from domain.categories import CATEGORIES

logger = logging.getLogger(__name__)


def ensure_data_dir() -> None:
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def check_database_health() -> tuple[bool, list[str]]:
    """
    Prüft beim Start ob die Datenbank erreichbar, konsistent und korrekt
    konfiguriert ist. Gibt (ok, meldungen) zurück. Bei ok=False ist die
    Anwendung nicht sicher startbar.
    """
    messages: list[str] = []
    try:
        with get_connection() as conn:
            # 1. Erreichbarkeit: bereits durch get_connection() sichergestellt

            # 2. Foreign Keys aktiv?
            fk_row = conn.execute("PRAGMA foreign_keys").fetchone()
            if not fk_row or fk_row[0] != 1:
                msg = "PRAGMA foreign_keys ist nicht aktiv — referentielle Integrität nicht gewährleistet."
                messages.append(msg)
                logger.warning("Healthcheck: %s", msg)

            # 3. WAL-Modus aktiv?
            jm_row = conn.execute("PRAGMA journal_mode").fetchone()
            if jm_row and jm_row[0].lower() != "wal":
                msg = f"Journal-Modus ist '{jm_row[0]}', erwartet 'wal'."
                messages.append(msg)
                logger.warning("Healthcheck: %s", msg)

            # 4. Integritätsprüfung
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


def initialize_database() -> None:
    ensure_data_dir()

    with get_connection() as connection:
        # WAL-Modus einmalig aktivieren; bleibt persistent in der DB-Datei gespeichert.
        # Vorteile: bessere Schreib-Performance, crash-sichere Commits,
        # Lesezugriffe blockieren keine Schreibvorgänge.
        result = connection.execute("PRAGMA journal_mode=WAL").fetchone()
        if result and result[0].lower() == "wal":
            logger.debug("WAL-Modus aktiv.")
        else:
            logger.warning("WAL-Modus konnte nicht aktiviert werden (journal_mode=%s).", result[0] if result else "?")

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

        # Ensure optional columns exist for older DBs
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN person_id INTEGER")
        except Exception:
            pass
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN category_id INTEGER")
        except Exception:
            pass
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN adult_count INTEGER DEFAULT 1")
        except Exception:
            pass
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN child_count INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN disability_degree INTEGER")
        except Exception:
            pass
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN evaluation_reason TEXT")
        except Exception:
            pass
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN total_income REAL")
        except Exception:
            pass
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN total_expenses REAL")
        except Exception:
            pass
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN free_income REAL")
        except Exception:
            pass
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN entitlement_limit REAL")
        except Exception:
            pass
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN hardship_limit REAL")
        except Exception:
            pass
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN evaluation_details TEXT")
        except Exception:
            pass
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN examiner_id INTEGER")
        except Exception:
            pass
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN evaluation_date TEXT")
        except Exception:
            pass
        # Ensure case_number column exists (older DBs may not have it)
        try:
            connection.execute("ALTER TABLE claims ADD COLUMN case_number TEXT")
        except Exception:
            pass

        seed_basic_data(connection)

        # Assign case numbers to existing claims that don't have one
        try:
            rows = connection.execute("SELECT id, case_number FROM claims ORDER BY id").fetchall()
            year = datetime.now(UTC).year
            for row in rows:
                if not row["case_number"]:
                    # find last existing sequence for this year
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

                    case_number = f"AS-{year}-{seq:06d}"
                    connection.execute(
                        "UPDATE claims SET case_number = ? WHERE id = ?",
                        (case_number, row["id"]),
                    )
            connection.commit()
        except Exception:
            # best effort; if this fails, leave existing rows unchanged
            pass

        def has_column(table_name: str, col: str) -> bool:
            cols = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
            return any(c[1] == col for c in cols)

        # Backwards compatibility: if an older table named 'claim' exists, ensure it has expected columns
        try:
            tbl = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='claim' LIMIT 1"
            ).fetchone()
            if tbl:
                # add missing columns to old `claim` table so code can work with both schemas
                try:
                    if not has_column('claim', 'person_id'):
                        connection.execute("ALTER TABLE claim ADD COLUMN person_id INTEGER")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'category_id'):
                        connection.execute("ALTER TABLE claim ADD COLUMN category_id INTEGER")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'case_number'):
                        connection.execute("ALTER TABLE claim ADD COLUMN case_number TEXT")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'adult_count'):
                        connection.execute("ALTER TABLE claim ADD COLUMN adult_count INTEGER DEFAULT 1")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'child_count'):
                        connection.execute("ALTER TABLE claim ADD COLUMN child_count INTEGER DEFAULT 0")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'disability_degree'):
                        connection.execute("ALTER TABLE claim ADD COLUMN disability_degree INTEGER")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'evaluation_reason'):
                        connection.execute("ALTER TABLE claim ADD COLUMN evaluation_reason TEXT")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'total_income'):
                        connection.execute("ALTER TABLE claim ADD COLUMN total_income REAL")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'total_expenses'):
                        connection.execute("ALTER TABLE claim ADD COLUMN total_expenses REAL")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'free_income'):
                        connection.execute("ALTER TABLE claim ADD COLUMN free_income REAL")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'entitlement_limit'):
                        connection.execute("ALTER TABLE claim ADD COLUMN entitlement_limit REAL")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'hardship_limit'):
                        connection.execute("ALTER TABLE claim ADD COLUMN hardship_limit REAL")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'evaluation_details'):
                        connection.execute("ALTER TABLE claim ADD COLUMN evaluation_details TEXT")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'examiner_id'):
                        connection.execute("ALTER TABLE claim ADD COLUMN examiner_id INTEGER")
                except Exception:
                    pass
                try:
                    if not has_column('claim', 'evaluation_date'):
                        connection.execute("ALTER TABLE claim ADD COLUMN evaluation_date TEXT")
                except Exception:
                    pass
                connection.commit()
        except Exception:
            pass

        try:
            if not has_column('locations', 'is_active'):
                connection.execute("ALTER TABLE locations ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
        except Exception:
            pass
        try:
            if not has_column('users', 'failed_attempts'):
                connection.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        try:
            if not has_column('users', 'locked_until'):
                connection.execute("ALTER TABLE users ADD COLUMN locked_until TEXT")
        except Exception:
            pass
        try:
            if not has_column('roles', 'is_active'):
                connection.execute("ALTER TABLE roles ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
        except Exception:
            pass

        # New columns for roadmap items 1-5
        try:
            if not has_column('claims', 'review_date'):
                connection.execute("ALTER TABLE claims ADD COLUMN review_date TEXT")
        except Exception:
            pass
        try:
            if not has_column('documents', 'expiry_date'):
                connection.execute("ALTER TABLE documents ADD COLUMN expiry_date TEXT")
        except Exception:
            pass
        try:
            if not has_column('users', 'must_change_password'):
                connection.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

        # claim_history table (idempotent via IF NOT EXISTS in the main executescript)
        try:
            connection.execute("""
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
                )
            """)
            connection.commit()
        except Exception:
            pass

        # Roadmap items 6-10 migrations
        try:
            if not has_column('claims', 'widerspruch_frist'):
                connection.execute("ALTER TABLE claims ADD COLUMN widerspruch_frist TEXT")
        except Exception:
            pass
        try:
            if not has_column('cards', 'block_reason'):
                connection.execute("ALTER TABLE cards ADD COLUMN block_reason TEXT")
        except Exception:
            pass
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS claim_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim_id INTEGER NOT NULL,
                    user_id INTEGER,
                    note_text TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            connection.commit()
        except Exception:
            pass
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS filter_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT NOT NULL,
                    filter_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            connection.commit()
        except Exception:
            pass

        # ── S1: Mandantenfähigkeit ────────────────────────────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS mandants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    short_name TEXT,
                    contact_email TEXT,
                    contact_phone TEXT,
                    address TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
        except Exception:
            pass
        try:
            if not has_column('users', 'mandant_id'):
                connection.execute("ALTER TABLE users ADD COLUMN mandant_id INTEGER REFERENCES mandants(id)")
                connection.commit()
        except Exception:
            pass
        # Seed default mandant
        try:
            exists = connection.execute("SELECT id FROM mandants WHERE name = 'Tischlein Deck Dich Vorarlberg'").fetchone()
            if not exists:
                connection.execute(
                    "INSERT INTO mandants (name, short_name, is_active) VALUES (?, ?, 1)",
                    ("Tischlein Deck Dich Vorarlberg", "TDV"),
                )
                connection.commit()
        except Exception:
            pass

        # ── S4: Benachrichtigungen ────────────────────────────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT,
                    reference_type TEXT,
                    reference_id INTEGER,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            connection.commit()
        except Exception:
            pass

        # ── S5: Termine / Appointments ────────────────────────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER,
                    claim_id INTEGER,
                    user_id INTEGER,
                    location_id INTEGER,
                    title TEXT NOT NULL,
                    appointment_date TEXT NOT NULL,
                    appointment_time TEXT,
                    duration_minutes INTEGER DEFAULT 30,
                    note TEXT,
                    status TEXT NOT NULL DEFAULT 'GEPLANT',
                    created_by INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE SET NULL,
                    FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE SET NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL,
                    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            connection.commit()
        except Exception:
            pass

        # ── S7: Archiv-Löschregeln ────────────────────────────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS archive_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL UNIQUE,
                    retention_days INTEGER NOT NULL DEFAULT 3650,
                    action TEXT NOT NULL DEFAULT 'ARCHIVE',
                    description TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    last_run_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
        except Exception:
            pass
        # Seed default archive rules
        try:
            default_rules = [
                ("claims",     3650, "ARCHIVE", "Anträge nach 10 Jahren archivieren"),
                ("persons",    3650, "ARCHIVE", "Personen nach 10 Jahren archivieren"),
                ("documents",  1825, "ARCHIVE", "Dokumente nach 5 Jahren archivieren"),
                ("cards",      1825, "ARCHIVE", "Karten nach 5 Jahren archivieren"),
                ("audit_logs", 2555, "DELETE",  "Audit-Logs nach 7 Jahren löschen"),
            ]
            for (et, rd, ac, desc) in default_rules:
                connection.execute(
                    "INSERT OR IGNORE INTO archive_rules (entity_type, retention_days, action, description) VALUES (?,?,?,?)",
                    (et, rd, ac, desc),
                )
            connection.commit()
        except Exception:
            pass

        # ── S8: Personen-Notizen ──────────────────────────────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS person_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL,
                    user_id INTEGER,
                    note_text TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            connection.commit()
        except Exception:
            pass

        # ── M8: Freigabe-Workflow ─────────────────────────────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim_id INTEGER NOT NULL,
                    requested_by INTEGER,
                    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    reviewed_by INTEGER,
                    reviewed_at TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    comment TEXT,
                    FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
                    FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE SET NULL,
                    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            connection.commit()
        except Exception:
            pass

        # ── M3: Dokument-Vorlagen ─────────────────────────────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS document_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    template_type TEXT NOT NULL DEFAULT 'BRIEF',
                    description TEXT,
                    body_text TEXT NOT NULL DEFAULT '',
                    category_id INTEGER,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_by INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
                    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            connection.commit()
        except Exception:
            pass

        # ── Anforderungen: Haushaltsmitglieder / Kinder ───────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS household_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim_id INTEGER NOT NULL,
                    person_id INTEGER,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    birth_date TEXT,
                    relationship TEXT NOT NULL DEFAULT 'Sonstiges',
                    is_primary INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
                    FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE SET NULL
                )
            """)
            connection.commit()
        except Exception:
            pass

        # ── Anforderungen: Alters-Alerts (20-Jahre-Logik) ─────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS age_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim_id INTEGER NOT NULL,
                    household_member_id INTEGER,
                    alert_type TEXT NOT NULL,
                    trigger_date TEXT NOT NULL,
                    message TEXT,
                    is_resolved INTEGER NOT NULL DEFAULT 0,
                    resolved_by INTEGER,
                    resolved_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
                    FOREIGN KEY (household_member_id) REFERENCES household_members(id) ON DELETE SET NULL,
                    FOREIGN KEY (resolved_by) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            connection.commit()
        except Exception:
            pass

        # ── Migration: Personen birth_date ────────────────────────────────────
        try:
            if not has_column('persons', 'birth_date'):
                connection.execute("ALTER TABLE persons ADD COLUMN birth_date TEXT")
                connection.commit()
        except Exception:
            pass

        # ── Migration: Personen card_expiry_import ────────────────────────────
        try:
            if not has_column('persons', 'card_expiry_import'):
                connection.execute("ALTER TABLE persons ADD COLUMN card_expiry_import TEXT")
                connection.commit()
        except Exception:
            pass

        # ── Migration: Prüfungszähler + Erstprüfer ────────────────────────────
        try:
            if not has_column('claims', 'evaluation_count'):
                connection.execute(
                    "ALTER TABLE claims ADD COLUMN evaluation_count INTEGER NOT NULL DEFAULT 0"
                )
                connection.commit()
        except Exception:
            pass
        try:
            if not has_column('claims', 'first_examiner_id'):
                connection.execute(
                    "ALTER TABLE claims ADD COLUMN first_examiner_id INTEGER"
                )
                connection.commit()
        except Exception:
            pass

        # ── Migration: Dokument-Vorlagen Erweiterung ─────────────────────────
        for col, defn in [
            ("docx_data",      "BLOB"),
            ("status_trigger", "TEXT"),
            ("version",        "INTEGER DEFAULT 1"),
        ]:
            try:
                if not has_column("document_templates", col):
                    connection.execute(
                        f"ALTER TABLE document_templates ADD COLUMN {col} {defn}"
                    )
                    connection.commit()
            except Exception:
                pass

        # ── Migration: Persönliche Mailkonten ─────────────────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS user_mail_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    smtp_host TEXT NOT NULL DEFAULT '',
                    smtp_port INTEGER NOT NULL DEFAULT 587,
                    smtp_user TEXT NOT NULL DEFAULT '',
                    smtp_password_enc TEXT DEFAULT '',
                    from_email TEXT NOT NULL DEFAULT '',
                    from_name TEXT DEFAULT '',
                    use_tls INTEGER NOT NULL DEFAULT 1,
                    signature_html TEXT DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            connection.commit()
        except Exception:
            pass

        # ── Migration: Wiedervorlagen ──────────────────────────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS wiedervorlagen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    due_date TEXT NOT NULL,
                    note TEXT,
                    claim_id INTEGER,
                    person_id INTEGER,
                    is_done INTEGER NOT NULL DEFAULT 0,
                    done_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE SET NULL,
                    FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE SET NULL
                )
            """)
            connection.commit()
        except Exception:
            pass

        # ── Migration: Erneute-Prüfung-Anfragen ───────────────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS re_evaluation_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim_id INTEGER NOT NULL,
                    requested_by INTEGER NOT NULL,
                    request_reason TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    reviewed_by INTEGER,
                    review_comment TEXT,
                    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TEXT,
                    consumed_at TEXT,
                    FOREIGN KEY (claim_id) REFERENCES claims(id),
                    FOREIGN KEY (requested_by) REFERENCES users(id),
                    FOREIGN KEY (reviewed_by) REFERENCES users(id)
                )
            """)
            connection.commit()
        except Exception:
            pass

        # ── Migration: Anspruch Wohnbeihilfe ──────────────────────────────────
        try:
            if not has_column('claims', 'has_housing_benefit'):
                connection.execute("ALTER TABLE claims ADD COLUMN has_housing_benefit INTEGER DEFAULT NULL")
                connection.commit()
        except Exception:
            pass
        try:
            if not has_column('claims', 'housing_benefit_note'):
                connection.execute("ALTER TABLE claims ADD COLUMN housing_benefit_note TEXT")
                connection.commit()
        except Exception:
            pass

        # ── Migration: Kategorie-Umbenennung Sozialhilfebezüger ───────────────
        try:
            from domain.categories import CATEGORY_RENAMES
            for old_name, new_name in CATEGORY_RENAMES.items():
                old_cat = connection.execute("SELECT id FROM categories WHERE name=?", (old_name,)).fetchone()
                new_cat = connection.execute("SELECT id FROM categories WHERE name=?", (new_name,)).fetchone()
                if old_cat and not new_cat:
                    connection.execute("UPDATE categories SET name=? WHERE name=?", (new_name, old_name))
                elif old_cat and new_cat:
                    # merge: update foreign keys auf neue ID, dann alte Kategorie löschen
                    connection.execute("UPDATE persons SET category_id=? WHERE category_id=?", (new_cat["id"], old_cat["id"]))
                    connection.execute("UPDATE claims SET category_id=? WHERE category_id=?", (new_cat["id"], old_cat["id"]))
                    connection.execute("DELETE FROM categories WHERE id=?", (old_cat["id"],))
            connection.commit()
        except Exception:
            pass

        # ── Migration: Supervisor-Rolle ───────────────────────────────────────
        try:
            connection.execute("INSERT OR IGNORE INTO roles (name) VALUES (?)", ("Supervisor",))
            connection.commit()
        except Exception:
            pass

        # ── Migration: Freiwillige-Rolle (kein Systemzugang) ─────────────────
        try:
            connection.execute("INSERT OR IGNORE INTO roles (name) VALUES (?)", ("Freiwillige",))
            connection.commit()
        except Exception:
            pass

        # ── M9: Unterlagen-Checklisten ────────────────────────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS checklist_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category_id INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS checklist_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    is_required INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (template_id) REFERENCES checklist_templates(id) ON DELETE CASCADE
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS claim_checklist_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim_id INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    is_required INTEGER NOT NULL DEFAULT 1,
                    is_checked INTEGER NOT NULL DEFAULT 0,
                    checked_by INTEGER,
                    checked_at TEXT,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
                    FOREIGN KEY (checked_by) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            connection.commit()
        except Exception:
            pass

        # ── Software-Update-Verlauf ───────────────────────────────────────────
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS update_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'SUCCESS',
                    changelog TEXT,
                    backup_path TEXT,
                    applied_migrations TEXT,
                    error_message TEXT,
                    applied_by INTEGER,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (applied_by) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS update_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    migration_file TEXT NOT NULL UNIQUE,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
        except Exception:
            pass

        # ── Migration: Haushaltsmitglieder-Kategorien ─────────────────────────
        try:
            if not has_column('household_members', 'category_id'):
                connection.execute(
                    "ALTER TABLE household_members ADD COLUMN category_id INTEGER REFERENCES categories(id)"
                )
                connection.commit()
        except Exception:
            pass


def seed_basic_data(connection: sqlite3.Connection) -> None:
    locations = [
        ("Bludenz",),
        ("Feldkirch",),
        ("Dornbirn",),
    ]

    roles = [
        ("Mitarbeiter",),
        ("Standortleitung",),
        ("Admin",),
    ]

    connection.executemany(
        "INSERT OR IGNORE INTO locations (name) VALUES (?)",
        locations,
    )

    connection.executemany(
        "INSERT OR IGNORE INTO roles (name) VALUES (?)",
        roles,
    )

    # seed categories from domain
    categories = [(name,) for name in CATEGORIES]
    connection.executemany(
        "INSERT OR IGNORE INTO categories (name) VALUES (?)",
        categories,
    )

    seed_settings(connection)

    import os, sys

    in_pytest = any(k in os.environ for k in ("PYTEST_CURRENT_TEST", "PYTEST_ADDOPTS", "PYTEST_RUNNING")) or any("pytest" in a for a in sys.argv)

    # Standard-Admin: immer aktiv mit bekanntem Passwort (auf neuem System sofort verwendbar)
    _ADMIN_DEFAULT_PW = "admin123" if in_pytest else "Admin2024!"

    admin_exists = connection.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if not admin_exists:
        connection.execute(
            """
            INSERT INTO users (
                full_name, username, password_hash, role_id, location_id, is_active
            ) VALUES (
                ?, ?, ?,
                (SELECT id FROM roles WHERE name = ?),
                (SELECT id FROM locations WHERE name = ?),
                1
            )
            """,
            (
                "System Administrator",
                "admin",
                PasswordService.hash_password(_ADMIN_DEFAULT_PW),
                "Admin",
                "Bludenz",
            ),
        )
        connection.commit()

    # Migration: admin der durch ältere Versionen deaktiviert angelegt wurde, reaktivieren
    try:
        inactive = connection.execute(
            "SELECT id FROM users WHERE username = 'admin' AND is_active = 0"
        ).fetchone()
        if inactive:
            connection.execute(
                "UPDATE users SET is_active = 1, failed_attempts = 0, locked_until = NULL, "
                "password_hash = ? WHERE username = 'admin'",
                (PasswordService.hash_password(_ADMIN_DEFAULT_PW),),
            )
            connection.commit()
    except Exception:
        pass

    if in_pytest:
        # Testbenutzer temporär anlegen damit Integrationstests funktionieren
        try:
            connection.execute(
                "UPDATE users SET password_hash = ?, is_active = 1, failed_attempts = 0, locked_until = NULL WHERE username = ?",
                (PasswordService.hash_password("admin123"), "admin"),
            )
            connection.commit()
        except Exception:
            pass
        test_worker = connection.execute("SELECT id FROM users WHERE username = 'mitarbeiter1'").fetchone()
        if not test_worker:
            try:
                connection.execute(
                    """
                    INSERT INTO users (
                        full_name, username, password_hash, role_id, location_id, is_active
                    ) VALUES (
                        ?, ?, ?,
                        (SELECT id FROM roles WHERE name = ?),
                        (SELECT id FROM locations WHERE name = ?),
                        1
                    )
                    """,
                    (
                        "Max Mitarbeiter",
                        "mitarbeiter1",
                        PasswordService.hash_password("Mitarbeiter2024!"),
                        "Mitarbeiter",
                        "Feldkirch",
                    ),
                )
                connection.commit()
            except Exception:
                pass

    connection.commit()
    seed_document_types(connection)
    seed_default_templates(connection)
    seed_claims(connection)


def seed_settings(connection: sqlite3.Connection) -> None:
    defaults = [
        (
            "BASE_LIMIT",
            "820.0",
            "number",
            "Anspruchsgrenzen",
            "Basisgrenze pro erwachsene Person.",
            1,
        ),
        (
            "ADDITIONAL_ADULT_LIMIT",
            "390.0",
            "number",
            "Anspruchsgrenzen",
            "Zuschlag für weitere erwachsene Haushaltsmitglieder.",
            1,
        ),
        (
            "CHILD_LIMIT",
            "185.0",
            "number",
            "Anspruchsgrenzen",
            "Zuschlag für Kinder.",
            1,
        ),
        (
            "HARDSHIP_FACTOR",
            "1.1",
            "number",
            "Härtefall",
            "Multiplikator zur Berechnung der Härtefallgrenze.",
            1,
        ),
        (
            "CASE_NUMBER_PREFIX",
            "AS",
            "string",
            "Fallnummern",
            "Präfix für generierte Fallnummern (z.B. AS → AS-2026-000001).",
            1,
        ),
        (
            "UPDATE_MANIFEST_URL",
            "",
            "string",
            "Updates",
            "URL zum Update-Manifest (JSON). Leer = kein Update-Server konfiguriert.",
            1,
        ),
    ]

    connection.executemany(
        "INSERT OR IGNORE INTO settings (key, value, value_type, category, description, editable_by_admin) VALUES (?, ?, ?, ?, ?, ?)",
        defaults,
    )
    connection.commit()


def seed_document_types(connection: sqlite3.Connection) -> None:
    document_types = [
        ("Ausweis", "Personalausweis, Reisepass oder ähnliche Identifikationsdokumente.", 1),
        ("Einkommensnachweis", "Lohnabrechnung, Gehaltsbescheinigung oder Einkommensnachweis.", 1),
        ("Haushaltsnachweis", "Nachweis über Haushaltsgröße, Kosten oder Bedarfssituation.", 1),
        ("Antrag", "Formulare oder Anträge zum Leistungsbezug.", 1),
        ("Prüfprotokoll", "Protokolle, Prüfberichte oder interne Dokumente zur Anspruchsprüfung.", 1),
        ("Bescheid", "Bescheide, Entscheidungen oder Schriftstücke mit hohem Beweiskraftwert.", 1),
        ("Kartenunterlage", "Unterlagen zur Kartenherstellung und Kartenausgabe.", 1),
        ("Sonstiges", "Weitere Dokumente ohne speziellen Typ.", 1),
    ]
    connection.executemany(
        "INSERT OR IGNORE INTO document_types (name, description, is_active) VALUES (?, ?, ?)",
        document_types,
    )
    connection.commit()


def seed_claims(connection: sqlite3.Connection) -> None:
    # Simple seed claims to allow UI to show examples
    example_claims = [
        {
            "username": "admin",
            "location": "Bludenz",
            "status": ClaimStatus.IN_PRUEFUNG,
            "description": "Erstmalige Beantragung von Unterstützung im Mai 2026.",
            "start_date": "2026-05-01",
            "end_date": "2026-05-31",
            "created_by": "admin",
        }
    ]

    for claim in example_claims:
        existing = connection.execute(
            "SELECT 1 FROM claims WHERE description = ? LIMIT 1",
            (claim["description"],),
        ).fetchone()

        if existing:
            continue

        # generate a simple case number
        year = datetime.now(UTC).year
        last = connection.execute(
            "SELECT case_number FROM claims WHERE case_number LIKE ? ORDER BY case_number DESC LIMIT 1",
            (f"AS-{year}-%",),
        ).fetchone()

        if last:
            try:
                seq = int(last["case_number"].split("-")[-1]) + 1
            except Exception:
                seq = 1
        else:
            seq = 1

        case_number = f"AS-{year}-{seq:06d}"

        connection.execute(
            """
            INSERT INTO claims (
                case_number,
                person_id,
                user_id,
                location_id,
                category_id,
                status,
                description,
                start_date,
                end_date,
                created_by
            ) VALUES (
                ?,
                NULL,
                (SELECT id FROM users WHERE username = ?),
                (SELECT id FROM locations WHERE name = ?),
                NULL,
                ?,
                ?,
                ?,
                ?,
                (SELECT id FROM users WHERE username = ?)
            )
            """,
            (
                case_number,
                claim["username"],
                claim["location"],
                claim["status"],
                claim["description"],
                claim["start_date"],
                claim["end_date"],
                claim["created_by"],
            ),
        )

    connection.commit()


def migrate_existing_claim_statuses(connection: sqlite3.Connection) -> None:
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


def seed_default_templates(connection: sqlite3.Connection) -> None:
    """Seeded Standard-Vorlagentexte.

    Prüft jeden Eintrag einzeln per Name — vorhandene Vorlagen werden NICHT überschrieben,
    fehlende werden nachgeseeded. Kein Härtefall-Template (ausdrücklich ausgenommen).
    """
    templates = [
        # ── 1. Anspruchsberechtigt ────────────────────────────────────────────
        {
            "name":           "Bescheid – Anspruchsberechtigt",
            "template_type":  "BESCHEID",
            "status_trigger": "ANSPRUCHSBERECHTIGT",
            "body_text": """\
{{ANREDE}},

im Namen des Vereins Tischlein Deck Dich Vorarlberg freuen wir uns, Ihnen mitteilen zu können, dass Ihr Antrag auf Unterstützungsleistungen nach eingehender Prüfung positiv beschieden wurde.

Aktenzeichen: {{AKTENZEICHEN}}
Prüfungsdatum: {{DATUM}}
Standort: {{STANDORT}}

Ergebnis der Prüfung:
Ihr Antrag wurde positiv bewertet. Sie sind damit berechtigt, die Leistungen des Vereins in Anspruch zu nehmen.

Begründung:
{{BEGRUENDUNG}}

Nächste Schritte:
Für die Ausstellung Ihrer persönlichen Kundenkarte wenden Sie sich bitte an den Standort {{STANDORT}}. Bringen Sie zu diesem Termin bitte einen gültigen Lichtbildausweis mit.

Die Karte wird auf Ihren Namen ausgestellt und ist ausschließlich für Ihre Person bestimmt.

Sollten Sie Fragen zu Ihrem Antrag oder zu den Leistungen des Vereins haben, stehen Ihnen die Mitarbeiterinnen und Mitarbeiter des Standorts {{STANDORT}} gerne zur Verfügung.

Mit freundlichen Grüßen

{{MITARBEITER}}
Verein Tischlein Deck Dich Vorarlberg
Ladritschweg 10c · 6773 Vandans""",
        },

        # ── 2. Abgelehnt ─────────────────────────────────────────────────────
        {
            "name":           "Bescheid – Abgelehnt",
            "template_type":  "BESCHEID",
            "status_trigger": "ABGELEHNT",
            "body_text": """\
{{ANREDE}},

nach eingehender Prüfung Ihres Antrags auf Unterstützungsleistungen beim Verein Tischlein Deck Dich Vorarlberg müssen wir Ihnen leider mitteilen, dass Ihrem Ansuchen nicht entsprochen werden kann.

Aktenzeichen: {{AKTENZEICHEN}}
Prüfungsdatum: {{DATUM}}
Standort: {{STANDORT}}

Ergebnis der Prüfung:
Ihr Antrag wurde abgelehnt.

Begründung:
{{BEGRUENDUNG}}

Die vollständige Begründung dieser Entscheidung entnehmen Sie bitte dem beigefügten Prüfungsprotokoll (Aktenzeichen {{AKTENZEICHEN}}).

Widerspruchsrecht:
Sie haben das Recht, innerhalb von 14 Tagen ab Zustellung dieses Bescheids schriftlich Widerspruch einzulegen. Richten Sie Ihren Widerspruch bitte unter Angabe des Aktenzeichens {{AKTENZEICHEN}} an den Standort {{STANDORT}}.

Neue Antragstellung:
Sollten sich Ihre persönlichen oder wirtschaftlichen Verhältnisse wesentlich ändern, steht Ihnen jederzeit die Möglichkeit offen, einen neuen Antrag zu stellen.

Wir bedanken uns für Ihr Vertrauen und bedauern, Ihnen keine positive Entscheidung mitteilen zu können.

Mit freundlichen Grüßen

{{MITARBEITER}}
Verein Tischlein Deck Dich Vorarlberg
Ladritschweg 10c · 6773 Vandans

Beilage: Prüfungsprotokoll (Aktenzeichen {{AKTENZEICHEN}})""",
        },

        # ── 3. Vorläufig Abgelehnt / Rückfrage ───────────────────────────────
        {
            "name":           "Bescheid – Vorläufig Abgelehnt",
            "template_type":  "BESCHEID",
            "status_trigger": "VORLAEFIG_ABGELEHNT",
            "body_text": """\
{{ANREDE}},

Ihr Antrag auf Unterstützungsleistungen beim Verein Tischlein Deck Dich Vorarlberg wurde einer ersten Prüfung unterzogen. Aufgrund fehlender oder unvollständiger Unterlagen kann derzeit keine abschließende Entscheidung getroffen werden.

Aktenzeichen: {{AKTENZEICHEN}}
Prüfungsdatum: {{DATUM}}
Standort: {{STANDORT}}

Ergebnis der Prüfung:
Vorläufig abgelehnt – weitere Abklärung erforderlich.

Begründung:
{{BEGRUENDUNG}}

Erforderliche Maßnahmen:
Damit Ihr Antrag weiterbearbeitet werden kann, bitten wir Sie, die fehlenden Unterlagen oder Informationen umgehend beim Standort {{STANDORT}} einzureichen.

Sobald alle erforderlichen Dokumente vollständig vorliegen, wird Ihr Antrag erneut geprüft und Sie werden schriftlich über das endgültige Ergebnis informiert.

Bitte beachten Sie, dass bei ausbleibender Rückmeldung innerhalb von 30 Tagen der Antrag als zurückgezogen gilt.

Für Rückfragen oder zur Terminvereinbarung wenden Sie sich bitte an den Standort {{STANDORT}}.

Mit freundlichen Grüßen

{{MITARBEITER}}
Verein Tischlein Deck Dich Vorarlberg
Ladritschweg 10c · 6773 Vandans""",
        },

        # ── 4. In Prüfung (Eingangsbestätigung) ──────────────────────────────
        {
            "name":           "Eingangsbestätigung – Antrag in Prüfung",
            "template_type":  "INFORMATION",
            "status_trigger": "IN_PRUEFUNG",
            "body_text": """\
{{ANREDE}},

wir bestätigen den Eingang Ihres Antrags auf Unterstützungsleistungen beim Verein Tischlein Deck Dich Vorarlberg und danken Ihnen für Ihr Vertrauen.

Aktenzeichen: {{AKTENZEICHEN}}
Eingangsdatum: {{DATUM}}
Standort: {{STANDORT}}
Aktueller Status: Antrag in Prüfung

Ihr Antrag wird derzeit von unseren Mitarbeiterinnen und Mitarbeitern sorgfältig geprüft. Sobald die Prüfung abgeschlossen ist, werden wir Sie schriftlich über das Ergebnis informieren.

Für eine zügige Bearbeitung bitten wir Sie, sicherzustellen, dass alle erforderlichen Unterlagen vollständig und lesbar vorliegen. Sollten noch Nachweise fehlen, werden wir Sie gesondert kontaktieren.

Bitte halten Sie bei allen Kontaktaufnahmen Ihr Aktenzeichen bereit: {{AKTENZEICHEN}}

Bei Fragen zum Stand Ihrer Bearbeitung stehen Ihnen die Mitarbeiterinnen und Mitarbeiter des Standorts {{STANDORT}} gerne zur Verfügung.

Mit freundlichen Grüßen

{{MITARBEITER}}
Verein Tischlein Deck Dich Vorarlberg
Ladritschweg 10c · 6773 Vandans""",
        },

        # ── 5. Freigabe Kundenkarte ───────────────────────────────────────────
        {
            "name":           "Mitteilung – Kundenkarte freigegeben",
            "template_type":  "INFORMATION",
            "status_trigger": "FREIGABE_KARTE",
            "body_text": """\
{{ANREDE}},

wir freuen uns, Ihnen mitteilen zu können, dass Ihre persönliche Kundenkarte für den Bezug von Leistungen des Vereins Tischlein Deck Dich Vorarlberg ausgestellt und zur Abholung bereitsteht.

Aktenzeichen: {{AKTENZEICHEN}}
Ausstellungsdatum: {{DATUM}}
Standort: {{STANDORT}}

Abholung Ihrer Kundenkarte:
Bitte holen Sie Ihre Karte persönlich beim Standort {{STANDORT}} ab. Bringen Sie dabei bitte einen gültigen Lichtbildausweis mit.

Wichtige Hinweise zur Nutzung Ihrer Kundenkarte:
– Die Karte ist personengebunden und nicht übertragbar.
– Sie ist ausschließlich für die im Antrag genannten Personen bestimmt.
– Das Ablaufdatum ist auf der Karte vermerkt. Rechtzeitig vor Ablauf erhalten Sie eine Erinnerung.
– Bei Verlust oder Diebstahl informieren Sie bitte umgehend den Standort {{STANDORT}}.

Mit der Kundenkarte sind Sie berechtigt, die Leistungen des Vereins im Rahmen Ihrer geprüften Anspruchsberechtigung zu nutzen.

Mit freundlichen Grüßen

{{MITARBEITER}}
Verein Tischlein Deck Dich Vorarlberg
Ladritschweg 10c · 6773 Vandans""",
        },

        # ── 6. Widerspruch erhalten ───────────────────────────────────────────
        {
            "name":           "Eingangsbestätigung – Widerspruch",
            "template_type":  "INFORMATION",
            "status_trigger": "WIDERSPRUCH",
            "body_text": """\
{{ANREDE}},

wir bestätigen den Eingang Ihres Widerspruchs zum Bescheid betreffend Ihren Antrag auf Unterstützungsleistungen beim Verein Tischlein Deck Dich Vorarlberg.

Aktenzeichen: {{AKTENZEICHEN}}
Eingang des Widerspruchs: {{DATUM}}
Standort: {{STANDORT}}

Ihr Widerspruch wird von uns sorgfältig geprüft. Dabei werden alle von Ihnen vorgebrachten Argumente und Unterlagen berücksichtigt. Wir werden Ihnen das Ergebnis dieser Prüfung innerhalb einer angemessenen Frist schriftlich mitteilen.

Falls Sie weitere Unterlagen oder Informationen zur Unterstützung Ihres Widerspruchs einreichen möchten, bitten wir Sie, dies baldmöglichst zu tun.

Bitte halten Sie bei allen Kontaktaufnahmen Ihr Aktenzeichen bereit: {{AKTENZEICHEN}}

Für Rückfragen zum Widerspruchsverfahren stehen Ihnen die Mitarbeiterinnen und Mitarbeiter des Standorts {{STANDORT}} gerne zur Verfügung.

Mit freundlichen Grüßen

{{MITARBEITER}}
Verein Tischlein Deck Dich Vorarlberg
Ladritschweg 10c · 6773 Vandans""",
        },
    ]

    for t in templates:
        # Einzeln nach Name prüfen — nur anlegen wenn noch nicht vorhanden
        try:
            exists = connection.execute(
                "SELECT id FROM document_templates WHERE name=?", (t["name"],)
            ).fetchone()
            if not exists:
                connection.execute(
                    """INSERT INTO document_templates
                       (name, template_type, description, body_text,
                        status_trigger, is_active, version, created_by)
                       VALUES (?,?,?,?,?,1,1,NULL)""",
                    (
                        t["name"],
                        t["template_type"],
                        f"Standard-Vorlage für: {t['name']}",
                        t["body_text"],
                        t.get("status_trigger"),
                    ),
                )
        except Exception:
            pass
    connection.commit()


def is_database_ready() -> bool:
    try:
        ensure_data_dir()
        with get_connection() as connection:
            connection.execute("SELECT 1")
        return True
    except sqlite3.Error:
        return False
