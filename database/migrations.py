"""Schema-Migrationssystem fuer Min Guata Lada.

Jede Migration ist eine idempotente Funktion die eine SQLite-Verbindung erhaelt.
`run_migrations()` wird von `initialize_database()` aufgerufen und wendet alle
noch nicht angewandten Migrationen in Reihenfolge an.

Neue Spalten oder Tabellen kommen ausschliesslich hierher — nie direkt in die
executescript()-Basisschema-Sektion von db.py.

Fuer PostgreSQL werden die Migrationen NICHT ausgefuehrt — das volle Schema wird
durch schema_postgres.sql angelegt. Die Versionen werden nur als "applied" markiert.
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _is_postgres(conn) -> bool:
    """True wenn conn eine PgConnectionAdapter-Instanz ist."""
    return not isinstance(conn, sqlite3.Connection)


def _col_exists(conn, table: str, col: str) -> bool:
    if _is_postgres(conn):
        row = conn.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = %s",
            (table, col),
        ).fetchone()
        return row is not None
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)


def _table_exists(conn, table: str) -> bool:
    if _is_postgres(conn):
        row = conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
            (table,),
        ).fetchone()
        return row is not None
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone())


def _add_col(conn, table: str, col: str, defn: str) -> None:
    if not _col_exists(conn, table, col):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")


# ── Migrationen ───────────────────────────────────────────────────────────────

def _m001_claims_early_columns(c: sqlite3.Connection) -> None:
    """Alte Antraege-DBs: optionale Spalten die spaeter in das Basisschema aufgenommen wurden."""
    for col, defn in [
        ("person_id",         "INTEGER"),
        ("category_id",       "INTEGER"),
        ("adult_count",       "INTEGER DEFAULT 1"),
        ("child_count",       "INTEGER DEFAULT 0"),
        ("disability_degree", "INTEGER"),
        ("evaluation_reason", "TEXT"),
        ("total_income",      "REAL"),
        ("total_expenses",    "REAL"),
        ("free_income",       "REAL"),
        ("entitlement_limit", "REAL"),
        ("hardship_limit",    "REAL"),
        ("evaluation_details","TEXT"),
        ("examiner_id",       "INTEGER"),
        ("evaluation_date",   "TEXT"),
        ("case_number",       "TEXT"),
    ]:
        _add_col(c, "claims", col, defn)


def _m002_legacy_claim_table(c: sqlite3.Connection) -> None:
    """Rueckwaertskompatibilitaet: alte 'claim'-Tabelle (umbenannt in 'claims')."""
    if not _table_exists(c, "claim"):
        return
    for col, defn in [
        ("person_id",         "INTEGER"),
        ("category_id",       "INTEGER"),
        ("case_number",       "TEXT"),
        ("adult_count",       "INTEGER DEFAULT 1"),
        ("child_count",       "INTEGER DEFAULT 0"),
        ("disability_degree", "INTEGER"),
        ("evaluation_reason", "TEXT"),
        ("total_income",      "REAL"),
        ("total_expenses",    "REAL"),
        ("free_income",       "REAL"),
        ("entitlement_limit", "REAL"),
        ("hardship_limit",    "REAL"),
        ("evaluation_details","TEXT"),
        ("examiner_id",       "INTEGER"),
        ("evaluation_date",   "TEXT"),
    ]:
        _add_col(c, "claim", col, defn)


def _m003_user_lockout(c: sqlite3.Connection) -> None:
    """Benutzer-Sperr-Spalten (Login-Schutz) und Rollen/Standort-Aktiv-Flag."""
    _add_col(c, "users",     "failed_attempts", "INTEGER NOT NULL DEFAULT 0")
    _add_col(c, "users",     "locked_until",    "TEXT")
    _add_col(c, "locations", "is_active",       "INTEGER NOT NULL DEFAULT 1")
    _add_col(c, "roles",     "is_active",       "INTEGER NOT NULL DEFAULT 1")


def _m004_review_date_and_password(c: sqlite3.Connection) -> None:
    """Wiedervorlage-Datum, Ablaufdatum fuer Dokumente, Passwort-Aenderungspflicht."""
    _add_col(c, "claims",    "review_date",          "TEXT")
    _add_col(c, "documents", "expiry_date",          "TEXT")
    _add_col(c, "users",     "must_change_password", "INTEGER NOT NULL DEFAULT 0")


def _m005_widerspruch_and_block_reason(c: sqlite3.Connection) -> None:
    """Widerspruchsfrist in Antraegen, Sperr-Grund in Karten."""
    _add_col(c, "claims", "widerspruch_frist", "TEXT")
    _add_col(c, "cards",  "block_reason",      "TEXT")


def _m006_mandants(c: sqlite3.Connection) -> None:
    """Mandantenfaehigkeit: mandants-Tabelle, users.mandant_id, Standard-Mandant."""
    c.execute("""
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
    _add_col(c, "users", "mandant_id", "INTEGER REFERENCES mandants(id)")
    if not c.execute("SELECT 1 FROM mandants WHERE name='Tischlein Deck Dich Vorarlberg'").fetchone():
        c.execute(
            "INSERT INTO mandants (name, short_name, is_active) VALUES (?, ?, 1)",
            ("Tischlein Deck Dich Vorarlberg", "TDV"),
        )


def _m007_notifications(c: sqlite3.Connection) -> None:
    """In-App-Benachrichtigungen."""
    c.execute("""
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


def _m008_appointments(c: sqlite3.Connection) -> None:
    """Terminverwaltung."""
    c.execute("""
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


def _m009_archive_rules(c: sqlite3.Connection) -> None:
    """Archivierungs-Regeln mit Standard-Konfiguration."""
    c.execute("""
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
    for entity_type, days, action, desc in [
        ("claims",     3650, "ARCHIVE", "Antraege nach 10 Jahren archivieren"),
        ("persons",    3650, "ARCHIVE", "Personen nach 10 Jahren archivieren"),
        ("documents",  1825, "ARCHIVE", "Dokumente nach 5 Jahren archivieren"),
        ("cards",      1825, "ARCHIVE", "Karten nach 5 Jahren archivieren"),
        ("audit_logs", 2555, "DELETE",  "Audit-Logs nach 7 Jahren loeschen"),
    ]:
        c.execute(
            "INSERT OR IGNORE INTO archive_rules (entity_type, retention_days, action, description) VALUES (?,?,?,?)",
            (entity_type, days, action, desc),
        )


def _m010_person_notes(c: sqlite3.Connection) -> None:
    """Personen-Notizen."""
    c.execute("""
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


def _m011_approval_requests(c: sqlite3.Connection) -> None:
    """Freigabe-Workflow fuer Antraege."""
    c.execute("""
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


def _m012_document_templates(c: sqlite3.Connection) -> None:
    """Dokumentvorlagen fuer automatisierte Schreiben."""
    c.execute("""
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


def _m013_household_members(c: sqlite3.Connection) -> None:
    """Haushaltsmitglieder fuer Anspruchspruefung (Kinder-Logik)."""
    c.execute("""
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


def _m014_age_alerts(c: sqlite3.Connection) -> None:
    """Alters-Alerts (20-Jahre-Logik)."""
    c.execute("""
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


def _m015_persons_extra_columns(c: sqlite3.Connection) -> None:
    """Geburtsdatum und Import-Ablaufdatum fuer Personen."""
    _add_col(c, "persons", "birth_date",         "TEXT")
    _add_col(c, "persons", "card_expiry_import",  "TEXT")


def _m016_claims_re_evaluation_columns(c: sqlite3.Connection) -> None:
    """Pruefungszaehler und Erstpruefer fuer Wiederholungspruefungs-Logik."""
    _add_col(c, "claims", "evaluation_count",  "INTEGER NOT NULL DEFAULT 0")
    _add_col(c, "claims", "first_examiner_id", "INTEGER")


def _m017_document_template_columns(c: sqlite3.Connection) -> None:
    """Dokumentvorlagen: DOCX-Daten, Status-Trigger, Versionshistorie."""
    for col, defn in [
        ("docx_data",      "BLOB"),
        ("status_trigger", "TEXT"),
        ("version",        "INTEGER DEFAULT 1"),
    ]:
        _add_col(c, "document_templates", col, defn)


def _m018_user_mail_configs(c: sqlite3.Connection) -> None:
    """Persoenliche SMTP-Mailkonten pro Benutzer."""
    c.execute("""
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


def _m019_wiedervorlagen(c: sqlite3.Connection) -> None:
    """Wiedervorlage-System fuer zeitbasierte Erinnerungen."""
    c.execute("""
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


def _m020_re_evaluation_requests(c: sqlite3.Connection) -> None:
    """Wiederholte-Pruefung-Anfragen mit Supervisor-Freigabe."""
    c.execute("""
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


def _m021_housing_benefit(c: sqlite3.Connection) -> None:
    """Wohnbeihilfe-Felder im Antrag."""
    _add_col(c, "claims", "has_housing_benefit",  "INTEGER DEFAULT NULL")
    _add_col(c, "claims", "housing_benefit_note", "TEXT")


def _m022_category_renames(c: sqlite3.Connection) -> None:
    """Kategorie-Umbenennung laut CATEGORY_RENAMES (Sozialhilfebezueger etc.)."""
    try:
        from domain.categories import CATEGORY_RENAMES
    except ImportError:
        return
    for old_name, new_name in CATEGORY_RENAMES.items():
        old_cat = c.execute("SELECT id FROM categories WHERE name=?", (old_name,)).fetchone()
        new_cat = c.execute("SELECT id FROM categories WHERE name=?", (new_name,)).fetchone()
        if old_cat and not new_cat:
            c.execute("UPDATE categories SET name=? WHERE name=?", (new_name, old_name))
        elif old_cat and new_cat:
            c.execute("UPDATE persons SET category_id=? WHERE category_id=?", (new_cat["id"], old_cat["id"]))
            c.execute("UPDATE claims  SET category_id=? WHERE category_id=?", (new_cat["id"], old_cat["id"]))
            c.execute("DELETE FROM categories WHERE id=?", (old_cat["id"],))


def _m023_role_seeds(c: sqlite3.Connection) -> None:
    """Supervisor- und Freiwilligen-Rollen (INSERT OR IGNORE)."""
    c.execute("INSERT OR IGNORE INTO roles (name) VALUES (?)", ("Supervisor",))
    c.execute("INSERT OR IGNORE INTO roles (name) VALUES (?)", ("Freiwillige",))


def _m024_checklists(c: sqlite3.Connection) -> None:
    """Unterlagen-Checklisten: Templates und Antrag-spezifische Items."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS checklist_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS checklist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            is_required INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (template_id) REFERENCES checklist_templates(id) ON DELETE CASCADE
        )
    """)
    c.execute("""
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


def _m025_update_history(c: sqlite3.Connection) -> None:
    """Software-Update-Verlauf und Migrations-Protokoll fuer den Update-Service."""
    c.execute("""
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS update_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            migration_file TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _m026_household_member_category(c: sqlite3.Connection) -> None:
    """Kategorie-Zuordnung fuer Haushaltsmitglieder."""
    _add_col(c, "household_members", "category_id", "INTEGER REFERENCES categories(id)")


def _m027_auto_check_updates_setting(c: sqlite3.Connection) -> None:
    """Settings: AUTO_CHECK_UPDATES-Eintrag fuer bestehende Installationen einfuegen."""
    c.execute(
        "INSERT OR IGNORE INTO settings "
        "(key, value, value_type, category, description, editable_by_admin) "
        "VALUES ('AUTO_CHECK_UPDATES', 'false', 'boolean', 'Updates', "
        "'Beim App-Start automatisch auf neue Versionen prüfen.', 1)"
    )


# ── Registrierung ─────────────────────────────────────────────────────────────

MIGRATIONS: list[tuple[int, str]] = [
    (1,  "claims: early compat columns"),
    (2,  "claims: legacy 'claim' table compat"),
    (3,  "users: lockout columns (failed_attempts, locked_until)"),
    (4,  "claims/documents/users: review_date, expiry_date, must_change_password"),
    (5,  "claims/cards: widerspruch_frist, block_reason"),
    (6,  "mandants: Tabelle + users.mandant_id + Seed"),
    (7,  "notifications: Benachrichtigungen"),
    (8,  "appointments: Terminverwaltung"),
    (9,  "archive_rules: Archivierungs-Regeln + Seed"),
    (10, "person_notes: Personen-Notizen"),
    (11, "approval_requests: Freigabe-Workflow"),
    (12, "document_templates: Dokumentvorlagen"),
    (13, "household_members: Haushaltsmitglieder"),
    (14, "age_alerts: Alters-Alerts (20-Jahre-Logik)"),
    (15, "persons: birth_date, card_expiry_import"),
    (16, "claims: evaluation_count, first_examiner_id"),
    (17, "document_templates: docx_data, status_trigger, version"),
    (18, "user_mail_configs: persoenliche Mailkonten"),
    (19, "wiedervorlagen: Wiedervorlage-System"),
    (20, "re_evaluation_requests: Wiederholungs-Pruefung"),
    (21, "claims: has_housing_benefit, housing_benefit_note"),
    (22, "categories: Kategorie-Umbenennung (CATEGORY_RENAMES)"),
    (23, "roles: Supervisor + Freiwillige Seeds"),
    (24, "checklists: Templates, Items, Claim-Items"),
    (25, "update_history + update_migrations Tabellen"),
    (26, "household_members: category_id"),
    (27, "settings: AUTO_CHECK_UPDATES Standardwert"),
]

_MIGRATION_FNS = {
    1:  _m001_claims_early_columns,
    2:  _m002_legacy_claim_table,
    3:  _m003_user_lockout,
    4:  _m004_review_date_and_password,
    5:  _m005_widerspruch_and_block_reason,
    6:  _m006_mandants,
    7:  _m007_notifications,
    8:  _m008_appointments,
    9:  _m009_archive_rules,
    10: _m010_person_notes,
    11: _m011_approval_requests,
    12: _m012_document_templates,
    13: _m013_household_members,
    14: _m014_age_alerts,
    15: _m015_persons_extra_columns,
    16: _m016_claims_re_evaluation_columns,
    17: _m017_document_template_columns,
    18: _m018_user_mail_configs,
    19: _m019_wiedervorlagen,
    20: _m020_re_evaluation_requests,
    21: _m021_housing_benefit,
    22: _m022_category_renames,
    23: _m023_role_seeds,
    24: _m024_checklists,
    25: _m025_update_history,
    26: _m026_household_member_category,
    27: _m027_auto_check_updates_setting,
}


def _ensure_migrations_table(conn) -> None:
    if _is_postgres(conn):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version    INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
    else:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()


def _applied_versions(conn) -> set[int]:
    return {r[0] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}


def run_migrations(conn) -> None:
    """
    Wendet alle noch nicht angewandten Migrationen in Reihenfolge an.
    Bei PostgreSQL ist das Schema bereits vollständig durch schema_postgres.sql
    angelegt — hier werden nur die Versionen als applied markiert.
    """
    _ensure_migrations_table(conn)
    applied = _applied_versions(conn)

    if _is_postgres(conn):
        # Schema already created by schema_postgres.sql; just record versions.
        placeholder = '%s'
        for version, description in MIGRATIONS:
            if version not in applied:
                conn.execute(
                    f"INSERT INTO schema_migrations (version, description) VALUES ({placeholder}, {placeholder})"
                    f" ON CONFLICT (version) DO NOTHING",
                    (version, description),
                )
        conn.commit()
        return

    for version, description in MIGRATIONS:
        if version in applied:
            continue
        logger.info("Migration %d anwenden: %s", version, description)
        try:
            _MIGRATION_FNS[version](conn)
            conn.commit()
            conn.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (version, description),
            )
            conn.commit()
            logger.debug("Migration %d erfolgreich.", version)
        except Exception as exc:
            logger.error("Migration %d fehlgeschlagen: %s", version, exc)
            conn.rollback()
            raise
