import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime

from app.config import DATA_DIR, DB_PATH
from core.claim_status import ClaimStatus
from services.password_service import PasswordService
from domain.categories import CATEGORIES


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


def initialize_database() -> None:
    ensure_data_dir()

    with get_connection() as connection:
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
            year = datetime.utcnow().year
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

    # Only create and print credentials if the admin user does not yet exist
    admin_exists = connection.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()

    if not admin_exists:
        if in_pytest:
            admin_pw = "admin123"
        else:
            admin_pw = PasswordService.generate_random_password(16)
        admin_password_hash = PasswordService.hash_password(admin_pw)
        admin_is_active = 1 if in_pytest else 0

        connection.execute(
            """
            INSERT INTO users (
                full_name, username, password_hash, role_id, location_id, is_active
            ) VALUES (
                ?, ?, ?,
                (SELECT id FROM roles WHERE name = ?),
                (SELECT id FROM locations WHERE name = ?),
                ?
            )
            """,
            ("System Administrator", "admin", admin_password_hash, "Admin", "Bludenz", admin_is_active),
        )
        connection.commit()
        try:
            print("ERSTANLAGE ADMIN-KONTO:")
            print(f"  Benutzername: admin")
            print(f"  Einmalpasswort: {admin_pw}")
            print("  Bitte das Passwort nach dem ersten Login sofort ändern und das Konto aktivieren.")
        except Exception:
            pass

    employee_exists = connection.execute("SELECT id FROM users WHERE username = 'mitarbeiter1'").fetchone()

    if not employee_exists:
        employee_pw = PasswordService.generate_random_password(14)
        employee_password_hash = PasswordService.hash_password(employee_pw)
        employee_is_active = 1 if in_pytest else 0

        connection.execute(
            """
            INSERT INTO users (
                full_name, username, password_hash, role_id, location_id, is_active
            ) VALUES (
                ?, ?, ?,
                (SELECT id FROM roles WHERE name = ?),
                (SELECT id FROM locations WHERE name = ?),
                ?
            )
            """,
            ("Max Mitarbeiter", "mitarbeiter1", employee_password_hash, "Mitarbeiter", "Feldkirch", employee_is_active),
        )
        connection.commit()

    if in_pytest:
        try:
            connection.execute(
                "UPDATE users SET password_hash = ?, is_active = 1, failed_attempts = 0, locked_until = NULL WHERE username = ?",
                (PasswordService.hash_password("admin123"), "admin"),
            )
            connection.execute(
                "UPDATE users SET is_active = 1, failed_attempts = 0, locked_until = NULL WHERE username = ?",
                ("mitarbeiter1",),
            )
            connection.commit()
        except Exception:
            pass

    connection.commit()
    seed_document_types(connection)
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
            "username": "mitarbeiter1",
            "location": "Feldkirch",
            "status": ClaimStatus.IN_PRUEFUNG,
            "description": "Erstmalige Beantragung von Unterstützung im Mai 2026.",
            "start_date": "2026-05-01",
            "end_date": "2026-05-31",
            "created_by": "mitarbeiter1",
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
        year = datetime.utcnow().year
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


def is_database_ready() -> bool:
    try:
        ensure_data_dir()
        with get_connection() as connection:
            connection.execute("SELECT 1")
        return True
    except sqlite3.Error:
        return False
