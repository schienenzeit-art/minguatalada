"""
Tests für die 4-Augen-Regel (ReEvaluationService).

Kernregel: Ein Mitarbeiter darf einen Antrag nur einmal eigenständig prüfen.
Jede weitere Prüfung erfordert Supervisor-Freigabe.
Privilegierte Rollen (Admin, Supervisor, Standortleitung) sind ausgenommen.

Diese Tests sichern die kritischste Geschäftsregel des Systems als Regression ab.
"""
import pytest

from core.claim_status import ClaimStatus
from tests.conftest import create_test_claim

pytestmark = pytest.mark.integration


# ─── Erste Prüfung ───────────────────────────────────────────────────────────

def test_erste_pruefung_ist_immer_erlaubt_fuer_mitarbeiter(db, as_mitarbeiter, re_eval_service):
    erlaubt, grund = re_eval_service.can_evaluate(claim_id=99, eval_count=0)
    assert erlaubt
    assert grund == ""


def test_erste_pruefung_ist_erlaubt_fuer_supervisor(db, as_supervisor, re_eval_service):
    erlaubt, grund = re_eval_service.can_evaluate(claim_id=99, eval_count=0)
    assert erlaubt


def test_erste_pruefung_ist_erlaubt_fuer_admin(db, as_admin, re_eval_service):
    erlaubt, grund = re_eval_service.can_evaluate(claim_id=99, eval_count=0)
    assert erlaubt


# ─── Zweite Prüfung (Sperr-Logik) ────────────────────────────────────────────

def test_zweite_pruefung_geblockt_fuer_mitarbeiter_ohne_freigabe(
    db, db_conn, as_mitarbeiter, re_eval_service
):
    claim_id = create_test_claim(db_conn)
    erlaubt, grund = re_eval_service.can_evaluate(claim_id, eval_count=1)
    assert not erlaubt
    assert "Supervisor" in grund or "Freigabe" in grund


def test_zweite_pruefung_erlaubt_fuer_supervisor(db, db_conn, as_supervisor, re_eval_service):
    claim_id = create_test_claim(db_conn)
    erlaubt, grund = re_eval_service.can_evaluate(claim_id, eval_count=1)
    assert erlaubt
    assert grund == ""


def test_zweite_pruefung_erlaubt_fuer_admin(db, db_conn, as_admin, re_eval_service):
    claim_id = create_test_claim(db_conn)
    erlaubt, grund = re_eval_service.can_evaluate(claim_id, eval_count=1)
    assert erlaubt


def test_dritte_pruefung_geblockt_ohne_neue_freigabe(
    db, db_conn, as_mitarbeiter, re_eval_service
):
    claim_id = create_test_claim(db_conn)
    erlaubt, _ = re_eval_service.can_evaluate(claim_id, eval_count=3)
    assert not erlaubt


# ─── Freigabe-Anfrage stellen ─────────────────────────────────────────────────

def test_mitarbeiter_kann_freigabe_anfordern(db, db_conn, as_mitarbeiter, re_eval_service):
    claim_id = create_test_claim(db_conn)
    request_id = re_eval_service.request_re_evaluation(claim_id, reason="Neue Unterlagen")
    assert isinstance(request_id, int)
    assert request_id > 0


def test_doppelte_freigabe_anfrage_wird_abgelehnt(
    db, db_conn, as_mitarbeiter, re_eval_service
):
    claim_id = create_test_claim(db_conn)
    re_eval_service.request_re_evaluation(claim_id)
    with pytest.raises(ValueError, match="offene Freigabe-Anfrage"):
        re_eval_service.request_re_evaluation(claim_id)


def test_freigabe_anfrage_blockiert_weitere_anfragen_im_status(
    db, db_conn, as_mitarbeiter, re_eval_service
):
    """Nach gestellter Anfrage: can_evaluate soll den Pending-Status melden."""
    claim_id = create_test_claim(db_conn)
    re_eval_service.request_re_evaluation(claim_id)
    erlaubt, grund = re_eval_service.can_evaluate(claim_id, eval_count=1)
    assert not erlaubt
    assert "angefordert" in grund.lower() or "ausstehend" in grund.lower()


def test_ohne_session_keine_freigabe_anfrage(db, db_conn, re_eval_service):
    from core.session import Session
    Session.clear()
    claim_id = create_test_claim(db_conn)
    with pytest.raises(PermissionError):
        re_eval_service.request_re_evaluation(claim_id)


# ─── Supervisor genehmigt Freigabe ───────────────────────────────────────────

def test_supervisor_genehmigt_freigabe_und_mitarbeiter_darf_prufen(
    db, db_conn, as_mitarbeiter, as_supervisor, re_eval_service
):
    claim_id = create_test_claim(db_conn)

    # Mitarbeiter stellt Anfrage
    from core.session import Session
    Session.set_user(as_mitarbeiter)
    request_id = re_eval_service.request_re_evaluation(claim_id, "Neue Unterlagen")

    # Supervisor genehmigt
    Session.set_user(as_supervisor)
    re_eval_service.approve(request_id, comment="OK")

    # Mitarbeiter kann jetzt prüfen
    Session.set_user(as_mitarbeiter)
    erlaubt, grund = re_eval_service.can_evaluate(claim_id, eval_count=1)
    assert erlaubt, f"Nach Genehmigung sollte Prüfung erlaubt sein, aber: {grund}"


def test_supervisor_lehnt_freigabe_ab(
    db, db_conn, as_mitarbeiter, as_supervisor, re_eval_service
):
    from core.session import Session
    claim_id = create_test_claim(db_conn)

    Session.set_user(as_mitarbeiter)
    request_id = re_eval_service.request_re_evaluation(claim_id)

    Session.set_user(as_supervisor)
    re_eval_service.reject(request_id, comment="Nicht gerechtfertigt")

    # Nach Ablehnung: Mitarbeiter kann nicht prüfen
    Session.set_user(as_mitarbeiter)
    erlaubt, _ = re_eval_service.can_evaluate(claim_id, eval_count=1)
    assert not erlaubt


def test_ablehnung_ohne_begruendung_wird_abgelehnt(
    db, db_conn, as_mitarbeiter, as_supervisor, re_eval_service
):
    from core.session import Session
    claim_id = create_test_claim(db_conn)

    Session.set_user(as_mitarbeiter)
    request_id = re_eval_service.request_re_evaluation(claim_id)

    Session.set_user(as_supervisor)
    with pytest.raises(ValueError, match="Pflichtfeld"):
        re_eval_service.reject(request_id, comment="")


def test_mitarbeiter_darf_nicht_genehmigen(
    db, db_conn, as_mitarbeiter, re_eval_service
):
    from core.session import Session
    claim_id = create_test_claim(db_conn)
    # Mit Mitarbeiter-Session: Anfrage stellen
    request_id = re_eval_service.request_re_evaluation(claim_id)

    # Derselbe Mitarbeiter versucht zu genehmigen → PermissionError
    with pytest.raises(PermissionError):
        re_eval_service.approve(request_id)


# ─── Freigabe verbrauchen ────────────────────────────────────────────────────

def test_genehmigte_freigabe_wird_nach_pruefung_verbraucht(
    db, db_conn, as_mitarbeiter, as_supervisor, re_eval_service
):
    from core.session import Session
    claim_id = create_test_claim(db_conn)

    Session.set_user(as_mitarbeiter)
    request_id = re_eval_service.request_re_evaluation(claim_id)

    Session.set_user(as_supervisor)
    re_eval_service.approve(request_id)

    # Freigabe verbrauchen (passiert nach erfolgreicher Prüfung)
    re_eval_service.consume_approved_request(claim_id)

    # Jetzt ist die Freigabe weg → erneut gesperrt
    Session.set_user(as_mitarbeiter)
    erlaubt, _ = re_eval_service.can_evaluate(claim_id, eval_count=2)
    assert not erlaubt


# ─── Lock-State UI-Hilfsmethode ──────────────────────────────────────────────

def test_lock_state_erste_pruefung_nicht_gesperrt(
    db, db_conn, as_mitarbeiter, re_eval_service
):
    claim_id = create_test_claim(db_conn)
    state = re_eval_service.get_claim_lock_state(claim_id, eval_count=0)
    assert not state["locked"]


def test_lock_state_nach_erster_pruefung_gesperrt_fuer_mitarbeiter(
    db, db_conn, as_mitarbeiter, re_eval_service
):
    claim_id = create_test_claim(db_conn)
    state = re_eval_service.get_claim_lock_state(claim_id, eval_count=1)
    assert state["locked"]


def test_lock_state_supervisor_nie_gesperrt(
    db, db_conn, as_supervisor, re_eval_service
):
    claim_id = create_test_claim(db_conn)
    state = re_eval_service.get_claim_lock_state(claim_id, eval_count=99)
    assert not state["locked"]
    assert state["privileged"]
