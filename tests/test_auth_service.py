"""
Tests für AuthService: Login-Szenarien, Lockout, deaktivierte Accounts.
Nutzt eine temporäre In-Memory-DB damit Produktionsdaten unberührt bleiben.
"""
import os
import pytest
import tempfile

os.environ.setdefault("PYTEST_RUNNING", "1")


@pytest.fixture(scope="module")
def db_path(tmp_path_factory):
    """Temporäre SQLite-DB pro Test-Modul."""
    p = tmp_path_factory.mktemp("db") / "test.db"
    return str(p)


@pytest.fixture(scope="module", autouse=True)
def init_db(db_path, monkeypatch_module):
    """Initialisiert DB in der temporären Datei."""
    import app.config as cfg
    from pathlib import Path
    monkeypatch_module.setattr(cfg, "DB_PATH", Path(db_path))
    monkeypatch_module.setattr(cfg, "DATA_DIR", Path(db_path).parent)
    from database import db
    monkeypatch_module.setattr(db, "DB_PATH", Path(db_path))
    db.initialize_database()


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch (pytest bietet nur function-scoped an)."""
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="module")
def auth(db_path, monkeypatch_module):
    from pathlib import Path
    import app.config as cfg
    import database.db as dbmod
    monkeypatch_module.setattr(cfg, "DB_PATH", Path(db_path))
    monkeypatch_module.setattr(dbmod, "DB_PATH", Path(db_path))
    from database.repositories.user_repository import UserRepository
    from services.auth_service import AuthService
    return AuthService(user_repository=UserRepository())


# ─── Hilfsfunktion ───────────────────────────────────────────────────────────

def _get_conn(db_path):
    import sqlite3
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


# ─── Basis-Tests ──────────────────────────────────────────────────────────────

def test_admin_login_success(auth):
    result = auth.login("admin", "admin123")
    assert result["success"] is True
    assert result["user"]["username"] == "admin"


def test_wrong_password(auth):
    result = auth.login("admin", "falschespasswort")
    assert result["success"] is False
    assert "falsch" in result["message"].lower()


def test_empty_credentials(auth):
    result = auth.login("", "")
    assert result["success"] is False
    assert "erforderlich" in result["message"].lower()


def test_unknown_user(auth):
    result = auth.login("gibtesnicht", "abc")
    assert result["success"] is False
    assert "nicht gefunden" in result["message"].lower()


# ─── Deaktivierter Account ────────────────────────────────────────────────────

def test_deactivated_user_cannot_login(auth, db_path):
    con = _get_conn(db_path)
    con.execute("UPDATE users SET is_active=0 WHERE username='admin'")
    con.commit(); con.close()

    result = auth.login("admin", "admin123")
    assert result["success"] is False
    assert "deaktiviert" in result["message"].lower() or "administrator" in result["message"].lower()

    # Wiederherstellen
    con = _get_conn(db_path)
    con.execute("UPDATE users SET is_active=1 WHERE username='admin'")
    con.commit(); con.close()


# ─── Gesperrter Account (locked_until in Zukunft) ────────────────────────────

def test_locked_user_cannot_login(auth, db_path):
    from datetime import datetime, timedelta, UTC
    future = (datetime.now(UTC) + timedelta(minutes=30)).isoformat()

    con = _get_conn(db_path)
    con.execute("UPDATE users SET locked_until=? WHERE username='admin'", (future,))
    con.commit(); con.close()

    result = auth.login("admin", "admin123")
    assert result["success"] is False
    assert "gesperrt" in result["message"].lower() or "administrator" in result["message"].lower()

    # Wiederherstellen
    con = _get_conn(db_path)
    con.execute("UPDATE users SET locked_until=NULL WHERE username='admin'")
    con.commit(); con.close()


def test_expired_lock_allows_login(auth, db_path):
    """Eine Sperre in der Vergangenheit darf den Login nicht blockieren."""
    from datetime import datetime, timedelta, UTC
    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()

    con = _get_conn(db_path)
    con.execute("UPDATE users SET locked_until=? WHERE username='admin'", (past,))
    con.commit(); con.close()

    result = auth.login("admin", "admin123")
    assert result["success"] is True

    con = _get_conn(db_path)
    con.execute("UPDATE users SET locked_until=NULL WHERE username='admin'")
    con.commit(); con.close()


# ─── must_change_password ─────────────────────────────────────────────────────

def test_must_change_password_flag(auth, db_path):
    con = _get_conn(db_path)
    con.execute("UPDATE users SET must_change_password=1 WHERE username='admin'")
    con.commit(); con.close()

    result = auth.login("admin", "admin123")
    assert result["success"] is True
    assert result["must_change_password"] is True

    con = _get_conn(db_path)
    con.execute("UPDATE users SET must_change_password=0 WHERE username='admin'")
    con.commit(); con.close()


# ─── Fehlversuchs-Lockout ─────────────────────────────────────────────────────

def test_failed_attempts_increment(auth, db_path):
    con = _get_conn(db_path)
    con.execute("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE username='admin'")
    con.commit(); con.close()

    for _ in range(3):
        auth.login("admin", "wrong")

    con = _get_conn(db_path)
    row = con.execute("SELECT failed_attempts FROM users WHERE username='admin'").fetchone()
    con.close()
    assert row["failed_attempts"] >= 3


def test_lockout_after_max_attempts(auth, db_path):
    """Nach MAX_FAILED_ATTEMPTS (5) wird locked_until gesetzt."""
    from services.auth_service import MAX_FAILED_ATTEMPTS
    con = _get_conn(db_path)
    con.execute("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE username='admin'")
    con.commit(); con.close()

    for _ in range(MAX_FAILED_ATTEMPTS):
        auth.login("admin", "wrong")

    con = _get_conn(db_path)
    row = con.execute("SELECT locked_until FROM users WHERE username='admin'").fetchone()
    con.close()
    assert row["locked_until"] is not None

    # Wiederherstellen
    con = _get_conn(db_path)
    con.execute("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE username='admin'")
    con.commit(); con.close()
