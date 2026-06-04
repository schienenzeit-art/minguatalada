"""
Gemeinsame Test-Fixtures für alle Test-Module.

Kernprinzip: Jede Test-Funktion/Klasse bekommt eine frische, isolierte
SQLite-Datenbank (tmp_path). Produktionsdaten bleiben unberührt.

Verwendung:
    def test_etwas(db, auth_service):
        ...

    @pytest.mark.integration
    def test_mit_echter_db(db):
        ...
"""
import os
import sys
from pathlib import Path

import pytest

# PYTEST_RUNNING früh setzen, damit seed_basic_data den Test-Admin anlegt
os.environ["PYTEST_RUNNING"] = "1"


# ─── Datenbank-Isolation ──────────────────────────────────────────────────────

@pytest.fixture()
def db(tmp_path, monkeypatch):
    """
    Isolierte SQLite-Testdatenbank in einem temporären Verzeichnis.

    Patcht sowohl `app.config` als auch `database.db` so, dass ALLE
    Repository-Importe auf diese Datenbank zeigen.
    Wird nach jedem Test automatisch gelöscht.
    """
    test_db = tmp_path / "test.db"
    test_data_dir = tmp_path

    # Alle Module die DB_PATH / DATA_DIR direkt importieren patchen
    import app.config as cfg
    import database.db as dbmod

    monkeypatch.setattr(cfg, "DB_PATH", test_db)
    monkeypatch.setattr(cfg, "DATA_DIR", test_data_dir)
    monkeypatch.setattr(dbmod, "DB_PATH", test_db)

    from database.db import initialize_database
    initialize_database()

    return test_db


@pytest.fixture()
def db_conn(db):
    """Rohe SQLite-Verbindung zur Testdatenbank für direkte SQL-Asserts."""
    import sqlite3
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    yield con
    con.close()


# ─── Session-Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_session_after_test():
    """Stellt sicher dass kein Session-State zwischen Tests überläuft."""
    yield
    from core.session import Session
    Session.clear()


@pytest.fixture()
def as_admin(db_conn):
    """Setzt eine Admin-Session. Gibt den User zurück."""
    from core.session import Session
    row = db_conn.execute(
        "SELECT u.*, r.name AS role_name FROM users u JOIN roles r ON u.role_id=r.id "
        "WHERE u.username='admin'"
    ).fetchone()
    user = dict(row)
    Session.set_user(user)
    yield user
    Session.clear()


@pytest.fixture()
def as_mitarbeiter(db, db_conn):
    """Legt einen Mitarbeiter-Testbenutzer an und setzt die Session."""
    from core.session import Session
    from services.password_service import PasswordService
    db_conn.execute(
        """INSERT OR IGNORE INTO users (full_name, username, password_hash, role_id, location_id, is_active)
           VALUES (?, ?, ?, (SELECT id FROM roles WHERE name='Mitarbeiter'),
                   (SELECT id FROM locations WHERE name='Feldkirch'), 1)""",
        ("Test Mitarbeiter", "testworker", PasswordService.hash_password("pw123")),
    )
    db_conn.commit()
    row = db_conn.execute(
        "SELECT u.*, r.name AS role_name FROM users u JOIN roles r ON u.role_id=r.id "
        "WHERE u.username='testworker'"
    ).fetchone()
    user = dict(row)
    Session.set_user(user)
    yield user
    Session.clear()


@pytest.fixture()
def as_supervisor(db, db_conn):
    """Legt einen Supervisor an und setzt die Session."""
    from core.session import Session
    from services.password_service import PasswordService
    db_conn.execute(
        """INSERT OR IGNORE INTO users (full_name, username, password_hash, role_id, location_id, is_active)
           VALUES (?, ?, ?, (SELECT id FROM roles WHERE name='Supervisor'),
                   (SELECT id FROM locations WHERE name='Bludenz'), 1)""",
        ("Test Supervisor", "testsupervisor", PasswordService.hash_password("sv123")),
    )
    db_conn.commit()
    row = db_conn.execute(
        "SELECT u.*, r.name AS role_name FROM users u JOIN roles r ON u.role_id=r.id "
        "WHERE u.username='testsupervisor'"
    ).fetchone()
    user = dict(row)
    Session.set_user(user)
    yield user
    Session.clear()


# ─── Service-Factories ────────────────────────────────────────────────────────

def make_claim_service(settings_service=None) -> "ClaimService":
    """Vollständig verdrahteter ClaimService für Tests – spiegelt build_service_container()."""
    from services.claim_service import ClaimService
    from services.settings_service import SettingsService
    from services.re_evaluation_service import ReEvaluationService
    from services.notification_service import NotificationService
    from services.audit_service import AuditService
    from database.repositories.claim_repository import ClaimRepository
    from database.repositories.income_repository import IncomeRepository
    from database.repositories.expense_repository import ExpenseRepository
    from database.repositories.re_evaluation_repository import ReEvaluationRepository
    from database.repositories.audit_repository import AuditRepository
    from database.repositories.notification_repository import NotificationRepository

    audit_svc = AuditService(repo=AuditRepository())
    return ClaimService(
        claim_repository=ClaimRepository(),
        income_repository=IncomeRepository(),
        expense_repository=ExpenseRepository(),
        settings_service=settings_service or SettingsService(),
        re_evaluation_service=ReEvaluationService(repo=ReEvaluationRepository(), audit_service=audit_svc),
        notification_service=NotificationService(repo=NotificationRepository()),
        audit_service=audit_svc,
    )


def make_re_eval_service() -> "ReEvaluationService":
    """Vollständig verdrahteter ReEvaluationService für Tests."""
    from services.re_evaluation_service import ReEvaluationService
    from database.repositories.re_evaluation_repository import ReEvaluationRepository
    return ReEvaluationService(repo=ReEvaluationRepository(), notification_service=None)


# ─── Service-Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture()
def auth_service(db):
    from database.repositories.user_repository import UserRepository
    from services.auth_service import AuthService
    return AuthService(user_repository=UserRepository())


@pytest.fixture()
def claim_service(db):
    return make_claim_service()


@pytest.fixture()
def re_eval_service(db):
    return make_re_eval_service()


@pytest.fixture()
def user_service(db):
    from services.user_service import UserService
    return UserService()


@pytest.fixture()
def update_service(db, tmp_path):
    from services.update_service import UpdateService
    svc = UpdateService()
    # Backup/Update-Verzeichnisse auf tmp_path umbiegen
    import services.update_service as usmod
    monkeypatch_attr = None  # wird in Tests direkt genutzt
    return svc


@pytest.fixture()
def audit_repo(db):
    from database.repositories.audit_repository import AuditRepository
    return AuditRepository()


# ─── Testdaten-Helpers ────────────────────────────────────────────────────────

def create_test_claim(db_conn, status="IN_PRUEFUNG", description="Testantrag") -> int:
    """Legt einen minimalen Testantrag an und gibt die ID zurück."""
    import datetime
    year = datetime.datetime.now().year
    # Eindeutige Nummer anhand timestamp
    seq = int(datetime.datetime.now().timestamp() * 1000) % 100000
    case_number = f"AS-{year}-T{seq:05d}"

    cur = db_conn.execute(
        """INSERT INTO claims
           (case_number, user_id, location_id, status, description)
           VALUES (?, (SELECT id FROM users WHERE username='admin'),
                   (SELECT id FROM locations WHERE name='Bludenz'),
                   ?, ?)""",
        (case_number, status, description),
    )
    db_conn.commit()
    return cur.lastrowid
