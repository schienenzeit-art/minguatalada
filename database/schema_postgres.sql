-- PostgreSQL schema for Min Guata Lada
-- Replaces the SQLite schema + all 26 Python migrations in one idempotent file.
-- Run once on a fresh database; safe to re-run (CREATE TABLE IF NOT EXISTS).

-- ─── Core lookup tables ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS locations (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS roles (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS mandants (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          TEXT    NOT NULL UNIQUE,
    short_name    TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    address       TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Users ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id                   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name            TEXT    NOT NULL,
    username             TEXT    NOT NULL UNIQUE,
    password_hash        TEXT    NOT NULL,
    role_id              INTEGER NOT NULL REFERENCES roles(id),
    location_id          INTEGER REFERENCES locations(id),
    mandant_id           INTEGER REFERENCES mandants(id),
    is_active            INTEGER NOT NULL DEFAULT 1,
    must_change_password INTEGER NOT NULL DEFAULT 0,
    failed_attempts      INTEGER NOT NULL DEFAULT 0,
    locked_until         TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Settings ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS settings (
    id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    key              TEXT    NOT NULL UNIQUE,
    value            TEXT    NOT NULL,
    value_type       TEXT    NOT NULL,
    category         TEXT,
    description      TEXT,
    editable_by_admin INTEGER NOT NULL DEFAULT 1,
    updated_by       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Persons ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS persons (
    id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name         TEXT NOT NULL,
    last_name          TEXT NOT NULL,
    address            TEXT NOT NULL,
    postal_code        TEXT NOT NULL,
    city               TEXT NOT NULL,
    email              TEXT,
    category_id        INTEGER REFERENCES categories(id),
    location_id        INTEGER REFERENCES locations(id),
    birth_date         TEXT,
    card_expiry_import TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Claims ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS claims (
    id                   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_number          TEXT    NOT NULL UNIQUE,
    person_id            INTEGER REFERENCES persons(id),
    user_id              INTEGER NOT NULL REFERENCES users(id),
    location_id          INTEGER NOT NULL REFERENCES locations(id),
    category_id          INTEGER REFERENCES categories(id),
    status               TEXT    NOT NULL,
    description          TEXT    NOT NULL,
    start_date           TEXT,
    end_date             TEXT,
    review_date          TEXT,
    widerspruch_frist    TEXT,
    created_by           INTEGER REFERENCES users(id),
    examiner_id          INTEGER REFERENCES users(id),
    first_examiner_id    INTEGER REFERENCES users(id),
    evaluation_date      TEXT,
    adult_count          INTEGER DEFAULT 1,
    child_count          INTEGER DEFAULT 0,
    disability_degree    INTEGER,
    evaluation_reason    TEXT,
    total_income         NUMERIC(12,4),
    total_expenses       NUMERIC(12,4),
    free_income          NUMERIC(12,4),
    entitlement_limit    NUMERIC(12,4),
    hardship_limit       NUMERIC(12,4),
    evaluation_details   TEXT,
    evaluation_count     INTEGER NOT NULL DEFAULT 0,
    has_housing_benefit  INTEGER,
    housing_benefit_note TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claim_history (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id    INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    changed_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    old_status  TEXT,
    new_status  TEXT NOT NULL,
    note        TEXT
);

CREATE TABLE IF NOT EXISTS claim_notes (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id   INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    note_text  TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Income / Expenses ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS incomes (
    id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    type     TEXT    NOT NULL,
    amount   NUMERIC(12,4) NOT NULL,
    note     TEXT
);

CREATE TABLE IF NOT EXISTS expenses (
    id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id  INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    type      TEXT    NOT NULL,
    amount    NUMERIC(12,4) NOT NULL,
    has_proof INTEGER NOT NULL DEFAULT 0,
    note      TEXT
);

-- ─── Cards ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cards (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    card_number  TEXT    NOT NULL UNIQUE,
    claim_id     INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    person_id    INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    location_id  INTEGER NOT NULL REFERENCES locations(id),
    issue_date   TEXT    NOT NULL,
    expiry_date  TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'AKTIV',
    block_reason TEXT,
    note         TEXT,
    created_by   INTEGER NOT NULL REFERENCES users(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Documents ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS document_types (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS documents (
    id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title              TEXT    NOT NULL,
    original_file_name TEXT    NOT NULL,
    file_name          TEXT    NOT NULL,
    storage_path       TEXT    NOT NULL,
    mime_type          TEXT    NOT NULL,
    file_size          INTEGER NOT NULL,
    document_type_id   INTEGER NOT NULL REFERENCES document_types(id),
    status             TEXT    NOT NULL,
    description        TEXT,
    claim_id           INTEGER REFERENCES claims(id),
    person_id          INTEGER REFERENCES persons(id),
    card_id            INTEGER REFERENCES cards(id),
    location_id        INTEGER REFERENCES locations(id),
    uploaded_by        INTEGER REFERENCES users(id),
    uploaded_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at        TIMESTAMPTZ,
    expiry_date        TEXT,
    is_deleted         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS document_templates (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           TEXT    NOT NULL,
    template_type  TEXT    NOT NULL DEFAULT 'BRIEF',
    description    TEXT,
    body_text      TEXT    NOT NULL DEFAULT '',
    docx_data      BYTEA,
    status_trigger TEXT,
    version        INTEGER DEFAULT 1,
    category_id    INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    is_active      INTEGER NOT NULL DEFAULT 1,
    created_by     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Tasks ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS tasks (
    id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title              TEXT    NOT NULL,
    description        TEXT,
    task_type          TEXT,
    status             TEXT    NOT NULL,
    priority           TEXT    NOT NULL,
    due_date           TEXT,
    assigned_user_id   INTEGER REFERENCES users(id),
    location_id        INTEGER REFERENCES locations(id),
    source_type        TEXT,
    source_ref_type    TEXT,
    source_ref_id      INTEGER,
    source_description TEXT,
    is_system_task     INTEGER NOT NULL DEFAULT 0,
    created_by         INTEGER REFERENCES users(id),
    completed_at       TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Audit / Notifications ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_logs (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id   INTEGER,
    details     TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id        INTEGER REFERENCES users(id) ON DELETE CASCADE,
    type           TEXT NOT NULL,
    title          TEXT NOT NULL,
    message        TEXT,
    reference_type TEXT,
    reference_id   INTEGER,
    is_read        INTEGER NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Appointments ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS appointments (
    id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    person_id          INTEGER REFERENCES persons(id) ON DELETE SET NULL,
    claim_id           INTEGER REFERENCES claims(id) ON DELETE SET NULL,
    user_id            INTEGER REFERENCES users(id) ON DELETE SET NULL,
    location_id        INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    title              TEXT    NOT NULL,
    appointment_date   TEXT    NOT NULL,
    appointment_time   TEXT,
    duration_minutes   INTEGER DEFAULT 30,
    note               TEXT,
    status             TEXT    NOT NULL DEFAULT 'GEPLANT',
    created_by         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Archive rules ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS archive_rules (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type    TEXT    NOT NULL UNIQUE,
    retention_days INTEGER NOT NULL DEFAULT 3650,
    action         TEXT    NOT NULL DEFAULT 'ARCHIVE',
    description    TEXT,
    is_active      INTEGER NOT NULL DEFAULT 1,
    last_run_at    TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Persons extras ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS person_notes (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    person_id   INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    note_text   TEXT    NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Approval workflow ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS approval_requests (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id     INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    requested_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at  TIMESTAMPTZ,
    status       TEXT NOT NULL DEFAULT 'PENDING',
    comment      TEXT
);

-- ─── Household members ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS household_members (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id     INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    person_id    INTEGER REFERENCES persons(id) ON DELETE SET NULL,
    category_id  INTEGER REFERENCES categories(id),
    first_name   TEXT NOT NULL,
    last_name    TEXT NOT NULL,
    birth_date   TEXT,
    relationship TEXT NOT NULL DEFAULT 'Sonstiges',
    is_primary   INTEGER NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS age_alerts (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id            INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    household_member_id INTEGER REFERENCES household_members(id) ON DELETE SET NULL,
    alert_type          TEXT NOT NULL,
    trigger_date        TEXT NOT NULL,
    message             TEXT,
    is_resolved         INTEGER NOT NULL DEFAULT 0,
    resolved_by         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Re-evaluation ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS re_evaluation_requests (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id       INTEGER NOT NULL REFERENCES claims(id),
    requested_by   INTEGER NOT NULL REFERENCES users(id),
    request_reason TEXT,
    status         TEXT NOT NULL DEFAULT 'PENDING',
    reviewed_by    INTEGER REFERENCES users(id),
    review_comment TEXT,
    requested_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at    TIMESTAMPTZ,
    consumed_at    TIMESTAMPTZ
);

-- ─── Mail config ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_mail_configs (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id           INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    smtp_host         TEXT    NOT NULL DEFAULT '',
    smtp_port         INTEGER NOT NULL DEFAULT 587,
    smtp_user         TEXT    NOT NULL DEFAULT '',
    smtp_password_enc TEXT    DEFAULT '',
    from_email        TEXT    NOT NULL DEFAULT '',
    from_name         TEXT    DEFAULT '',
    use_tls           INTEGER NOT NULL DEFAULT 1,
    signature_html    TEXT    DEFAULT '',
    is_active         INTEGER NOT NULL DEFAULT 1,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Wiedervorlagen ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS wiedervorlagen (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    due_date   TEXT    NOT NULL,
    note       TEXT,
    claim_id   INTEGER REFERENCES claims(id) ON DELETE SET NULL,
    person_id  INTEGER REFERENCES persons(id) ON DELETE SET NULL,
    is_done    INTEGER NOT NULL DEFAULT 0,
    done_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Checklists ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS checklist_templates (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS checklist_items (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    template_id INTEGER NOT NULL REFERENCES checklist_templates(id) ON DELETE CASCADE,
    label       TEXT    NOT NULL,
    is_required INTEGER NOT NULL DEFAULT 1,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS claim_checklist_items (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id   INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    label      TEXT    NOT NULL,
    is_required INTEGER NOT NULL DEFAULT 1,
    is_checked  INTEGER NOT NULL DEFAULT 0,
    checked_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    checked_at  TIMESTAMPTZ,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- ─── Update tracking ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS update_history (
    id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version            TEXT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'SUCCESS',
    changelog          TEXT,
    backup_path        TEXT,
    applied_migrations TEXT,
    error_message      TEXT,
    applied_by         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    applied_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS update_migrations (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version        TEXT NOT NULL,
    migration_file TEXT NOT NULL UNIQUE,
    applied_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Filter presets ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS filter_presets (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    filter_json TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Schema migration tracking ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    description TEXT    NOT NULL,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Seed data ────────────────────────────────────────────────────────────────

INSERT INTO locations (name, is_active) VALUES
    ('Bludenz',   1),
    ('Feldkirch', 1),
    ('Dornbirn',  1)
ON CONFLICT (name) DO NOTHING;

INSERT INTO roles (name, is_active) VALUES
    ('Admin',       1),
    ('Mitarbeiter', 1),
    ('Supervisor',  1),
    ('Freiwillige', 1)
ON CONFLICT (name) DO NOTHING;

INSERT INTO categories (name) VALUES
    ('Sozialhilfebezüger'),
    ('Flüchtling / Asylsuchender'),
    ('IV-Bezüger'),
    ('AHV-Bezüger'),
    ('Andere')
ON CONFLICT (name) DO NOTHING;

INSERT INTO mandants (name, short_name, is_active) VALUES
    ('Tischlein Deck Dich Vorarlberg', 'TDV', 1)
ON CONFLICT (name) DO NOTHING;

INSERT INTO archive_rules (entity_type, retention_days, action, description) VALUES
    ('claims',     3650, 'ARCHIVE', 'Antraege nach 10 Jahren archivieren'),
    ('persons',    3650, 'ARCHIVE', 'Personen nach 10 Jahren archivieren'),
    ('documents',  1825, 'ARCHIVE', 'Dokumente nach 5 Jahren archivieren'),
    ('cards',      1825, 'ARCHIVE', 'Karten nach 5 Jahren archivieren'),
    ('audit_logs', 2555, 'DELETE',  'Audit-Logs nach 7 Jahren loeschen')
ON CONFLICT (entity_type) DO NOTHING;
