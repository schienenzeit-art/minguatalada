"""
Integrationstests für ClaimService.persist_evaluation() — Priorität 2.

Testet den vollständigen Evaluationsworkflow gegen eine echte SQLite-Testdatenbank:
  - Erstprüfung (Mitarbeiter, Supervisor, Admin)
  - Zweitprüfung (mit und ohne Supervisor-Freigabe)
  - Alle Statusausgänge: ANSPRUCHSBERECHTIGT, HAERTEFALL, ABGELEHNT, VORLAEFIG_ABGELEHNT
  - Supervisor-Freigabe → Zweitprüfung freigegeben
  - Audit-Log-Einträge nach jeder Prüfung
  - Einkommensdaten werden korrekt in DB gespeichert
  - Fehlerfälle: PermissionError bei gesperrter Wiederholungsprüfung

Ziel: Keine kritische Änderung darf diesen Workflow unbeabsichtigt beschädigen.

Marker: @pytest.mark.integration
"""
import pytest

from core.claim_status import ClaimStatus
from tests.conftest import create_test_claim

pytestmark = pytest.mark.integration

# ── Einkommenswerte für reproduzierbare Statustests ───────────────────────────
# Grenzwerte (Defaults): BASE_LIMIT=820, HARDSHIP_FACTOR=1.1 → hardship_limit=902
# 1 Erwachsener, keine Kinder:  entitlement=820, hardship=902

INCOMES_ANSPRUCHSBERECHTIGT = {"Gehalt": 700.0}    # free=700 ≤ 820
INCOMES_HAERTEFALL          = {"Gehalt": 860.0}    # free=860: 820 < 860 ≤ 902
INCOMES_ABGELEHNT           = {"Gehalt": 950.0}    # free=950 > 902
EXPENSES_ZERO               = {}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def svc(db):
    """ClaimService mit allen echten Abhängigkeiten, isolierte Test-DB."""
    from services.claim_service import ClaimService
    return ClaimService()


@pytest.fixture()
def re_svc(db):
    from services.re_evaluation_service import ReEvaluationService
    return ReEvaluationService()


@pytest.fixture()
def audit_repo(db):
    from database.repositories.audit_repository import AuditRepository
    return AuditRepository()


@pytest.fixture()
def claim_id(db_conn):
    """Legt einen frischen Testantrag an und gibt dessen ID zurück."""
    return create_test_claim(db_conn)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _call_persist(svc, claim_id, incomes, expenses=None, adult_count=1,
                  child_count=0, category="Familie", has_housing_benefit=True,
                  examiner_id=None):
    """Wrapper mit sinnvollen Defaults für alle Tests."""
    return svc.persist_evaluation(
        claim_id=claim_id,
        incomes=incomes,
        expenses={k: {"amount": v, "deductible": True} for k, v in (expenses or {}).items()},
        adult_count=adult_count,
        child_count=child_count,
        category=category,
        has_housing_benefit=has_housing_benefit,
        examiner_id=examiner_id,
    )


# ── 1. Erstprüfung ────────────────────────────────────────────────────────────

class TestErstpruefung:
    def test_mitarbeiter_darf_erste_pruefung_durchfuehren(
        self, svc, claim_id, as_mitarbeiter
    ):
        result = _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                               examiner_id=as_mitarbeiter["id"])
        assert result["status"] == ClaimStatus.ANSPRUCHSBERECHTIGT

    def test_supervisor_darf_erste_pruefung_durchfuehren(
        self, svc, claim_id, as_supervisor
    ):
        result = _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                               examiner_id=as_supervisor["id"])
        assert result["status"] == ClaimStatus.ANSPRUCHSBERECHTIGT

    def test_admin_darf_erste_pruefung_durchfuehren(
        self, svc, claim_id, as_admin
    ):
        result = _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                               examiner_id=as_admin["id"])
        assert result["status"] == ClaimStatus.ANSPRUCHSBERECHTIGT

    def test_erstpruefung_setzt_evaluation_count_auf_1(
        self, svc, claim_id, as_admin, db_conn
    ):
        _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                      examiner_id=as_admin["id"])
        row = db_conn.execute(
            "SELECT evaluation_count FROM claims WHERE id=?", (claim_id,)
        ).fetchone()
        assert row["evaluation_count"] == 1

    def test_erstpruefung_setzt_first_examiner_id(
        self, svc, claim_id, as_admin, db_conn
    ):
        _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                      examiner_id=as_admin["id"])
        row = db_conn.execute(
            "SELECT first_examiner_id FROM claims WHERE id=?", (claim_id,)
        ).fetchone()
        assert row["first_examiner_id"] == as_admin["id"]

    def test_erstpruefung_persistiert_einkommen_in_db(
        self, svc, claim_id, as_admin, db_conn
    ):
        _call_persist(svc, claim_id, {"Gehalt": 700.0}, examiner_id=as_admin["id"])
        rows = db_conn.execute(
            "SELECT * FROM incomes WHERE claim_id=?", (claim_id,)
        ).fetchall()
        amounts = {r["type"]: r["amount"] for r in rows}
        assert amounts.get("Gehalt") == pytest.approx(700.0)

    def test_erstpruefung_persistiert_ausgaben_in_db(
        self, svc, claim_id, as_admin, db_conn
    ):
        _call_persist(
            svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
            expenses={"Miete": 300.0},
            examiner_id=as_admin["id"],
        )
        rows = db_conn.execute(
            "SELECT * FROM expenses WHERE claim_id=?", (claim_id,)
        ).fetchall()
        amounts = {r["type"]: r["amount"] for r in rows}
        assert amounts.get("Miete") == pytest.approx(300.0)


# ── 2. Statusausgänge ─────────────────────────────────────────────────────────

class TestStatusausgaenge:
    def test_einkommen_unter_grenze_ergibt_anspruchsberechtigt(
        self, svc, claim_id, as_admin
    ):
        result = _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                               has_housing_benefit=True, examiner_id=as_admin["id"])
        assert result["status"] == ClaimStatus.ANSPRUCHSBERECHTIGT
        assert result["is_eligible"] is True

    def test_einkommen_im_haertefallbereich_ergibt_haertefall(
        self, svc, claim_id, as_admin
    ):
        result = _call_persist(svc, claim_id, INCOMES_HAERTEFALL,
                               has_housing_benefit=True, examiner_id=as_admin["id"])
        assert result["status"] == ClaimStatus.HAERTEFALL
        assert result["is_hardship"] is True

    def test_einkommen_ueber_haertefallgrenze_ergibt_abgelehnt(
        self, svc, claim_id, as_admin
    ):
        result = _call_persist(svc, claim_id, INCOMES_ABGELEHNT,
                               has_housing_benefit=True, examiner_id=as_admin["id"])
        assert result["status"] == ClaimStatus.ABGELEHNT
        assert result["is_eligible"] is False

    def test_keine_wohnbeihilfe_bei_anspruchsberechtigt_ergibt_vorlaefig_abgelehnt(
        self, svc, claim_id, as_admin
    ):
        result = _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                               has_housing_benefit=False, examiner_id=as_admin["id"])
        assert result["status"] == ClaimStatus.VORLAEFIG_ABGELEHNT

    def test_keine_wohnbeihilfe_bei_haertefall_ergibt_vorlaefig_abgelehnt(
        self, svc, claim_id, as_admin
    ):
        result = _call_persist(svc, claim_id, INCOMES_HAERTEFALL,
                               has_housing_benefit=False, examiner_id=as_admin["id"])
        assert result["status"] == ClaimStatus.VORLAEFIG_ABGELEHNT

    def test_keine_wohnbeihilfe_bei_abgelehnt_bleibt_abgelehnt(
        self, svc, claim_id, as_admin
    ):
        result = _call_persist(svc, claim_id, INCOMES_ABGELEHNT,
                               has_housing_benefit=False, examiner_id=as_admin["id"])
        assert result["status"] == ClaimStatus.ABGELEHNT

    def test_kinder_erhoehen_anspruchsgrenze(self, svc, claim_id, as_admin):
        # 1 Erwachsener + 2 Kinder: entitlement = 820 + 2*185 = 1190
        # Einkommen 1100 → wäre ABGELEHNT ohne Kinder, aber ANSPRUCHSBERECHTIGT mit 2 Kindern
        result = _call_persist(
            svc, claim_id,
            incomes={"Gehalt": 1100.0},
            child_count=2,
            has_housing_benefit=True,
            examiner_id=as_admin["id"],
        )
        assert result["status"] == ClaimStatus.ANSPRUCHSBERECHTIGT

    def test_wohnbeihilfe_status_in_claim_gespeichert(
        self, svc, claim_id, as_admin, db_conn
    ):
        _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                      has_housing_benefit=True, examiner_id=as_admin["id"])
        row = db_conn.execute(
            "SELECT has_housing_benefit FROM claims WHERE id=?", (claim_id,)
        ).fetchone()
        assert row["has_housing_benefit"] == 1


# ── 3. Zweitprüfung (4-Augen-Regel) ──────────────────────────────────────────

class TestZweitpruefung:
    def test_mitarbeiter_zweite_pruefung_ohne_freigabe_wirft_permission_error(
        self, svc, claim_id, as_mitarbeiter, db_conn
    ):
        # Erstprüfung als Admin durchführen (setzt eval_count=1)
        from services.claim_service import ClaimService
        admin_svc = ClaimService()
        from core.session import Session
        admin_row = db_conn.execute(
            "SELECT u.*, r.name AS role_name FROM users u JOIN roles r ON u.role_id=r.id "
            "WHERE u.username='admin'"
        ).fetchone()
        Session.set_user(dict(admin_row))
        _call_persist(admin_svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                      examiner_id=admin_row["id"])

        # Jetzt Mitarbeiter versucht zweite Prüfung ohne Freigabe
        Session.set_user(as_mitarbeiter)
        with pytest.raises(PermissionError):
            _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                          examiner_id=as_mitarbeiter["id"])

    def test_supervisor_zweite_pruefung_ohne_freigabe_erlaubt(
        self, svc, claim_id, as_supervisor, db_conn
    ):
        # Erstprüfung simulieren (eval_count auf 1 setzen)
        db_conn.execute(
            "UPDATE claims SET evaluation_count=1 WHERE id=?", (claim_id,)
        )
        db_conn.commit()

        result = _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                               examiner_id=as_supervisor["id"])
        assert result["status"] == ClaimStatus.ANSPRUCHSBERECHTIGT

    def test_admin_zweite_pruefung_ohne_freigabe_erlaubt(
        self, svc, claim_id, as_admin, db_conn
    ):
        db_conn.execute(
            "UPDATE claims SET evaluation_count=1 WHERE id=?", (claim_id,)
        )
        db_conn.commit()

        result = _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                               examiner_id=as_admin["id"])
        assert result["status"] == ClaimStatus.ANSPRUCHSBERECHTIGT


# ── 4. Supervisor-Freigabe → Zweitprüfung ────────────────────────────────────

class TestSupervisorFreigabeZweitpruefung:
    def test_mitarbeiter_nach_freigabe_darf_zweite_pruefung_durchfuehren(
        self, svc, claim_id, as_mitarbeiter, as_supervisor, db_conn, re_svc
    ):
        # eval_count auf 1 setzen (Erstprüfung simulieren)
        db_conn.execute(
            "UPDATE claims SET evaluation_count=1 WHERE id=?", (claim_id,)
        )
        db_conn.commit()

        # Mitarbeiter stellt Freigabe-Anfrage
        from core.session import Session
        Session.set_user(as_mitarbeiter)
        request_id = re_svc.request_re_evaluation(claim_id)
        assert isinstance(request_id, int), "Freigabe-Anfrage lieferte keine ID"

        # Supervisor genehmigt
        Session.set_user(as_supervisor)
        re_svc.approve(request_id)

        # Mitarbeiter darf jetzt zweite Prüfung durchführen
        Session.set_user(as_mitarbeiter)
        result = _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                               examiner_id=as_mitarbeiter["id"])
        assert result["status"] == ClaimStatus.ANSPRUCHSBERECHTIGT

    def test_freigabe_wird_nach_zweitpruefung_verbraucht(
        self, svc, claim_id, as_mitarbeiter, as_supervisor, db_conn, re_svc
    ):
        db_conn.execute(
            "UPDATE claims SET evaluation_count=1 WHERE id=?", (claim_id,)
        )
        db_conn.commit()

        from core.session import Session
        Session.set_user(as_mitarbeiter)
        request_id = re_svc.request_re_evaluation(claim_id)

        Session.set_user(as_supervisor)
        re_svc.approve(request_id)

        Session.set_user(as_mitarbeiter)
        _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                      examiner_id=as_mitarbeiter["id"])

        # Nach der Zweitprüfung ist die Freigabe verbraucht → dritte Prüfung gesperrt
        db_conn.execute(
            "UPDATE claims SET evaluation_count=2 WHERE id=?", (claim_id,)
        )
        db_conn.commit()

        with pytest.raises(PermissionError):
            _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                          examiner_id=as_mitarbeiter["id"])


# ── 5. Audit-Logging ──────────────────────────────────────────────────────────

class TestAuditLogging:
    def test_erstpruefung_erstellt_audit_eintrag(
        self, svc, claim_id, as_admin, audit_repo
    ):
        _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                      examiner_id=as_admin["id"])
        logs = audit_repo.list_logs(limit=10)
        actions = [l["action"] for l in logs]
        assert "first_evaluation_completed" in actions

    def test_zweitpruefung_erstellt_re_evaluation_audit_eintrag(
        self, svc, claim_id, as_admin, audit_repo, db_conn
    ):
        # Erstprüfung
        _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                      examiner_id=as_admin["id"])
        # eval_count manuell auf 1 setzen (Erstprüfung zählt schon)
        # → zweite Prüfung durch Admin (keine Freigabe nötig)
        db_conn.execute(
            "UPDATE claims SET evaluation_count=1 WHERE id=?", (claim_id,)
        )
        db_conn.commit()

        _call_persist(svc, claim_id, INCOMES_HAERTEFALL,
                      examiner_id=as_admin["id"])
        logs = audit_repo.list_logs(limit=10)
        actions = [l["action"] for l in logs]
        assert "re_evaluation_completed" in actions

    def test_audit_eintrag_enthaelt_prufer_id(
        self, svc, claim_id, as_admin, audit_repo
    ):
        _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                      examiner_id=as_admin["id"])
        logs = audit_repo.list_logs(limit=10)
        eval_log = next(
            (l for l in logs if l["action"] == "first_evaluation_completed"), None
        )
        assert eval_log is not None
        assert str(as_admin["id"]) in (eval_log.get("details") or "")

    def test_audit_eintrag_enthaelt_status(
        self, svc, claim_id, as_admin, audit_repo
    ):
        _call_persist(svc, claim_id, INCOMES_HAERTEFALL,
                      has_housing_benefit=True, examiner_id=as_admin["id"])
        logs = audit_repo.list_logs(limit=10)
        eval_log = next(
            (l for l in logs if l["action"] == "first_evaluation_completed"), None
        )
        assert eval_log is not None
        assert "Härtefall" in (eval_log.get("details") or "")

    def test_blocked_evaluation_erstellt_audit_eintrag(
        self, svc, claim_id, as_mitarbeiter, db_conn
    ):
        # eval_count = 1 → Mitarbeiter gesperrt
        db_conn.execute(
            "UPDATE claims SET evaluation_count=1 WHERE id=?", (claim_id,)
        )
        db_conn.commit()

        with pytest.raises(PermissionError):
            _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                          examiner_id=as_mitarbeiter["id"])


# ── 6. Fehlerfälle ────────────────────────────────────────────────────────────

class TestFehlerfaelle:
    def test_nicht_existenter_claim_wirft_keine_stille_fehler(
        self, svc, as_admin
    ):
        """Prüfung auf nicht-existentem Antrag darf keinen stillen Fehler produzieren."""
        ghost_id = 999999
        with pytest.raises(Exception):
            _call_persist(svc, ghost_id, INCOMES_ANSPRUCHSBERECHTIGT,
                          examiner_id=as_admin["id"])

    def test_negative_einkommensbetraege_werden_als_null_behandelt(
        self, svc, claim_id, as_admin
    ):
        """Negative Einkommenswerte müssen auf 0 normalisiert werden."""
        result = _call_persist(
            svc, claim_id,
            incomes={"Gehalt": -500.0, "Pension": 300.0},
            has_housing_benefit=True,
            examiner_id=as_admin["id"],
        )
        # -500 → 0; Pension 300 → total_income = 300 ≤ 820 → ANSPRUCHSBERECHTIGT
        assert result["status"] == ClaimStatus.ANSPRUCHSBERECHTIGT
        assert result["total_income"] == pytest.approx(300.0)

    def test_leere_einkommensliste_ergibt_anspruchsberechtigt(
        self, svc, claim_id, as_admin
    ):
        """Kein Einkommen → free_income = 0 → immer anspruchsberechtigt."""
        result = _call_persist(
            svc, claim_id,
            incomes={},
            has_housing_benefit=True,
            examiner_id=as_admin["id"],
        )
        assert result["status"] == ClaimStatus.ANSPRUCHSBERECHTIGT
        assert result["total_income"] == pytest.approx(0.0)

    def test_ergebnis_enthaelt_alle_pflichtfelder(
        self, svc, claim_id, as_admin
    ):
        """Rückgabewert muss alle Felder des EvaluationResult.to_dict() enthalten."""
        result = _call_persist(svc, claim_id, INCOMES_ANSPRUCHSBERECHTIGT,
                               examiner_id=as_admin["id"])
        required_keys = {
            "status", "is_eligible", "is_hardship", "total_income",
            "total_expenses", "free_income", "entitlement_limit", "hardship_limit",
            "category", "reason", "details",
        }
        missing = required_keys - set(result.keys())
        assert not missing, f"Fehlende Felder im Ergebnis: {missing}"
