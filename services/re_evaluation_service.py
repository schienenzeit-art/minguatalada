"""Erneute-Prüfung-Service.

Schützt die Regel:
  Mitarbeiter darf einen neuen Antrag nur einmal eigenständig prüfen.
  Jede weitere Prüfung erfordert Supervisor-Freigabe.

Privilegierte Rollen (Supervisor, Admin, Standortleitung) sind ausgenommen.
"""
from core.session import Session
from database.repositories.re_evaluation_repository import ReEvaluationRepository

_PRIVILEGED_ROLES = frozenset({"Admin", "Supervisor", "Standortleitung"})


class ReEvaluationService:

    def __init__(
        self,
        repo: ReEvaluationRepository,
        audit_service=None,
        notification_service=None,
    ):
        self.repo = repo
        self._audit = audit_service
        self._notification = notification_service

    # ── Kernprüfung ───────────────────────────────────────────────────────────
    def can_evaluate(self, claim_id: int, eval_count: int) -> tuple[bool, str]:
        """Gibt (erlaubt, Fehlermeldung) zurück.

        eval_count: der aktuelle Prüfungszähler des Antrags (aus claims.evaluation_count).
        """
        role = (Session.get_user() or {}).get("role_name", "")

        # Privilegierte Rollen dürfen immer prüfen
        if role in _PRIVILEGED_ROLES:
            return True, ""

        # Erste Prüfung immer erlaubt
        if eval_count == 0:
            return True, ""

        # Prüfe auf genehmigte, noch nicht verbrauchte Freigabe
        approved = self.repo.get_approved_unused_for_claim(claim_id)
        if approved:
            return True, ""

        # Prüfe ob Anfrage bereits gestellt wurde
        pending = self.repo.get_pending_for_claim(claim_id)
        if pending:
            ts = (pending.get("requested_at") or "")[:16].replace("T", " ")
            return (
                False,
                f"Freigabe zur erneuten Prüfung bereits angefordert ({ts}). "
                "Bitte warten Sie auf die Supervisor-Entscheidung.",
            )

        return (
            False,
            "Dieser Antrag wurde bereits geprüft. "
            "Für eine erneute Prüfung ist eine Supervisor-Freigabe erforderlich. "
            "Nutzen Sie 'Freigabe anfordern'.",
        )

    # ── Anfragen ──────────────────────────────────────────────────────────────
    def request_re_evaluation(self, claim_id: int, reason: str | None = None) -> int:
        """Erstellt eine Freigabe-Anfrage für erneute Prüfung."""
        user_id = Session.get_user_id()
        if not user_id:
            raise PermissionError("Kein angemeldeter Benutzer.")

        # Keine doppelte Anfrage
        pending = self.repo.get_pending_for_claim(claim_id)
        if pending:
            raise ValueError(
                "Es existiert bereits eine offene Freigabe-Anfrage für diesen Antrag."
            )

        request_id = self.repo.create_request(claim_id, user_id, reason)

        self._audit_log(
            "re_evaluation_requested", "claim", claim_id,
            f"Erneute Prüfung angefordert durch User {user_id}. Grund: {reason or '(kein Grund)'}"
        )

        if self._notification:
            try:
                from database.db import get_connection
                with get_connection() as conn:
                    row = conn.execute(
                        "SELECT case_number FROM claims WHERE id=?", (claim_id,)
                    ).fetchone()
                case_number = row["case_number"] if row else str(claim_id)
                requester_name = (Session.get_user() or {}).get("full_name", f"User {user_id}")
                self._notification.notify_re_evaluation_requested(
                    case_number=case_number,
                    claim_id=claim_id,
                    requester_name=requester_name,
                    reason=reason,
                )
            except Exception:
                pass

        return request_id

    def consume_approved_request(self, claim_id: int) -> None:
        """Markiert die genehmigte Freigabe-Anfrage als verbraucht."""
        approved = self.repo.get_approved_unused_for_claim(claim_id)
        if approved:
            self.repo.consume(approved["id"])
            self._audit_log(
                "re_evaluation_consumed", "claim", claim_id,
                f"Genehmigte Freigabe (ID {approved['id']}) für erneute Prüfung verbraucht."
            )

    # ── Supervisor-Aktionen ───────────────────────────────────────────────────
    def approve(self, request_id: int, comment: str | None = None) -> None:
        """Supervisor genehmigt erneute Prüfung."""
        reviewer_id = Session.get_user_id()
        if not reviewer_id:
            raise PermissionError("Kein angemeldeter Benutzer.")

        role = (Session.get_user() or {}).get("role_name", "")
        if role not in _PRIVILEGED_ROLES:
            raise PermissionError(
                "Nur Supervisor / Standortleitung / Admin dürfen Freigaben erteilen."
            )

        req = self.repo.get_by_id(request_id)
        if not req:
            raise ValueError("Anfrage nicht gefunden.")
        if req["status"] != "PENDING":
            raise ValueError("Anfrage ist nicht mehr offen.")

        self.repo.review(request_id, reviewer_id, "APPROVED", comment)
        self._audit_log(
            "re_evaluation_approved", "claim", req["claim_id"],
            f"Freigabe zur erneuten Prüfung erteilt durch User {reviewer_id}."
            + (f" Kommentar: {comment}" if comment else "")
        )

    def reject(self, request_id: int, comment: str) -> None:
        """Supervisor lehnt erneute Prüfung ab."""
        if not comment or not comment.strip():
            raise ValueError("Ablehnungsgrund ist Pflichtfeld.")

        reviewer_id = Session.get_user_id()
        role = (Session.get_user() or {}).get("role_name", "")
        if role not in _PRIVILEGED_ROLES:
            raise PermissionError(
                "Nur Supervisor / Standortleitung / Admin dürfen Anfragen ablehnen."
            )

        req = self.repo.get_by_id(request_id)
        if not req:
            raise ValueError("Anfrage nicht gefunden.")
        if req["status"] != "PENDING":
            raise ValueError("Anfrage ist nicht mehr offen.")

        self.repo.review(request_id, reviewer_id, "REJECTED", comment.strip())
        self._audit_log(
            "re_evaluation_rejected", "claim", req["claim_id"],
            f"Freigabe abgelehnt durch User {reviewer_id}. Grund: {comment.strip()}"
        )

    # ── Listenabfragen ────────────────────────────────────────────────────────
    def list_pending(self) -> list[dict]:
        return self.repo.list_pending()

    def list_for_claim(self, claim_id: int) -> list[dict]:
        return self.repo.list_all(claim_id=claim_id)

    def count_pending(self) -> int:
        return self.repo.count_pending()

    def get_claim_lock_state(self, claim_id: int, eval_count: int) -> dict:
        """Gibt vollständigen Lock-State für UI-Darstellung zurück."""
        role = (Session.get_user() or {}).get("role_name", "")
        if role in _PRIVILEGED_ROLES:
            return {"locked": False, "privileged": True, "reason": "", "pending_request": None, "approved_request": None}

        if eval_count == 0:
            return {"locked": False, "privileged": False, "reason": "", "pending_request": None, "approved_request": None}

        approved = self.repo.get_approved_unused_for_claim(claim_id)
        if approved:
            return {"locked": False, "privileged": False, "reason": "Freigabe zur erneuten Prüfung erteilt.", "pending_request": None, "approved_request": approved}

        pending = self.repo.get_pending_for_claim(claim_id)
        if pending:
            ts = (pending.get("requested_at") or "")[:16].replace("T", " ")
            return {
                "locked": True, "privileged": False,
                "reason": f"Freigabe angefordert am {ts} – Entscheidung ausstehend.",
                "pending_request": pending, "approved_request": None,
            }

        return {
            "locked": True, "privileged": False,
            "reason": "Erste Prüfung bereits durchgeführt. Erneute Prüfung nur mit Supervisor-Freigabe.",
            "pending_request": None, "approved_request": None,
        }

    # ── Intern ────────────────────────────────────────────────────────────────
    def _audit_log(self, action: str, obj_type: str, obj_id: int | None, details: str) -> None:
        if self._audit:
            try:
                self._audit.log(action, obj_type, obj_id, details)
            except Exception:
                pass
        else:
            try:
                from services.audit_service import AuditService
                AuditService().log(action, obj_type, obj_id, details)
            except Exception:
                pass
