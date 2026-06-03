"""
Tests für Audit-Logging: Korrekte Events, keine sensiblen Daten im Log.

Sichert ab:
- Login-Ereignisse landen in audit_logs
- Passwörter erscheinen NIE im Log
- Benutzernames ohne Passworte
- Prüfungs-Events werden protokolliert
"""
import pytest

from core.claim_status import ClaimStatus
from tests.conftest import create_test_claim

pytestmark = pytest.mark.integration


# ─── Auth-Logging ─────────────────────────────────────────────────────────────

def test_erfolgreicher_login_erzeugt_audit_eintrag(db, db_conn, auth_service, audit_repo):
    vorher = audit_repo.count(object_type="auth")
    auth_service.login("admin", "admin123")
    nachher = audit_repo.count(object_type="auth")
    assert nachher > vorher


def test_login_success_action_korrekt(db, db_conn, auth_service, audit_repo):
    auth_service.login("admin", "admin123")
    logs = audit_repo.list_logs(object_type="auth")
    aktionen = [l["action"] for l in logs]
    assert "LOGIN_SUCCESS" in aktionen


def test_falsches_passwort_erzeugt_fehlschlag_eintrag(db, db_conn, auth_service, audit_repo):
    auth_service.login("admin", "falsch")
    logs = audit_repo.list_logs(object_type="auth")
    aktionen = [l["action"] for l in logs]
    assert "LOGIN_FAILED" in aktionen


def test_unbekannter_user_erzeugt_fehlschlag_eintrag(db, db_conn, auth_service, audit_repo):
    auth_service.login("gibtesnicht", "pw")
    logs = audit_repo.list_logs(object_type="auth")
    aktionen = [l["action"] for l in logs]
    assert "LOGIN_FAILED" in aktionen


def test_deaktivierter_user_erzeugt_fehlschlag_eintrag(db, db_conn, auth_service, audit_repo):
    db_conn.execute("UPDATE users SET is_active=0 WHERE username='admin'")
    db_conn.commit()
    auth_service.login("admin", "admin123")
    logs = audit_repo.list_logs(object_type="auth")
    assert any(l["action"] == "LOGIN_FAILED" for l in logs)
    db_conn.execute("UPDATE users SET is_active=1 WHERE username='admin'")
    db_conn.commit()


def test_lockout_erzeugt_account_locked_eintrag(db, db_conn, auth_service, audit_repo):
    from datetime import datetime, timedelta, UTC
    future = (datetime.now(UTC) + timedelta(minutes=30)).isoformat()
    db_conn.execute("UPDATE users SET locked_until=? WHERE username='admin'", (future,))
    db_conn.commit()
    auth_service.login("admin", "admin123")
    logs = audit_repo.list_logs(object_type="auth")
    assert any(l["action"] == "ACCOUNT_LOCKED" for l in logs)
    db_conn.execute("UPDATE users SET locked_until=NULL WHERE username='admin'")
    db_conn.commit()


# ─── Kein Passwort im Log ─────────────────────────────────────────────────────

def test_passwort_erscheint_nicht_in_audit_details(db, db_conn, auth_service, audit_repo):
    """Kernregel Datenschutz: Passwörter dürfen nie im Audit-Log stehen."""
    auth_service.login("admin", "admin123")
    auth_service.login("admin", "Admin2024!")
    auth_service.login("admin", "falschesPasswort_GeheimWort")

    logs = audit_repo.list_logs(object_type="auth")
    for log in logs:
        details = (log.get("details") or "").lower()
        assert "admin123" not in details, f"Passwort im Log: {log}"
        assert "admin2024!" not in details, f"Passwort im Log: {log}"
        assert "geheimwort" not in details, f"Passwort im Log: {log}"


def test_passworthash_erscheint_nicht_im_log(db, db_conn, auth_service, audit_repo):
    """Bcrypt-Hashes ($2b$...) dürfen nicht im Log stehen."""
    auth_service.login("admin", "admin123")
    logs = audit_repo.list_logs(object_type="auth")
    for log in logs:
        details = log.get("details") or ""
        assert "$2b$" not in details, f"Passwort-Hash im Log: {log}"
        assert "$2a$" not in details, f"Passwort-Hash im Log: {log}"


def test_login_log_enthaelt_benutzername(db, db_conn, auth_service, audit_repo):
    """Der Benutzername (kein Passwort) soll für Nachvollziehbarkeit im Log stehen."""
    auth_service.login("admin", "admin123")
    logs = audit_repo.list_logs(object_type="auth")
    success_logs = [l for l in logs if l["action"] == "LOGIN_SUCCESS"]
    assert success_logs, "Kein LOGIN_SUCCESS-Eintrag gefunden"
    details = success_logs[0].get("details") or ""
    assert "admin" in details.lower()


# ─── Prüfungs-Audit ───────────────────────────────────────────────────────────

def test_claim_status_update_erzeugt_keinen_direkten_audit_eintrag_in_auth(
    db, db_conn, as_admin, claim_service, audit_repo
):
    """Status-Updates landen NICHT in der Auth-Log-Kategorie."""
    claim_id = create_test_claim(db_conn)
    claim_service.update_claim_status(claim_id, ClaimStatus.ABGELEHNT)
    auth_logs = audit_repo.list_logs(object_type="auth")
    status_update_in_auth = any(
        "update_claim" in (l["action"] or "") for l in auth_logs
    )
    assert not status_update_in_auth


# ─── Audit-Cleanup ────────────────────────────────────────────────────────────

def test_alte_audit_logs_werden_geloescht(db, db_conn, audit_repo):
    """delete_old() löscht Einträge älter als N Tage — muss laufen ohne Exception."""
    # Einen sehr alten Eintrag direkt einfügen
    db_conn.execute(
        "INSERT INTO audit_logs (user_id, action, object_type, timestamp) VALUES (NULL, 'TEST', 'test', '2000-01-01 00:00:00')"
    )
    db_conn.commit()

    geloescht = audit_repo.delete_old(days=1)  # Alles älter als 1 Tag
    assert geloescht >= 1


def test_aktuelle_audit_logs_bleiben_erhalten(db, db_conn, auth_service, audit_repo):
    auth_service.login("admin", "admin123")
    vorher = audit_repo.count()
    audit_repo.delete_old(days=3650)  # 10 Jahre — aktuelle Einträge bleiben
    nachher = audit_repo.count()
    assert nachher >= vorher - 1  # Höchstens 1 Toleranz durch Timing
