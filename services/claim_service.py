from datetime import datetime, UTC
from typing import Optional, Dict, List

from app.ports import ClaimRepositoryPort, ExpenseRepositoryPort, IncomeRepositoryPort
from core.claim_status import ClaimStatus
from core.session import Session
from database.repositories.claim_repository import ClaimRepository
from database.repositories.claim_note_repository import ClaimNoteRepository
from database.repositories.income_repository import IncomeRepository
from database.repositories.expense_repository import ExpenseRepository
from services.pruefung_service import PruefungService
from services.settings_service import SettingsService


class ClaimService:
    def __init__(
        self,
        claim_repository: ClaimRepositoryPort | None = None,
        income_repository: IncomeRepositoryPort | None = None,
        expense_repository: ExpenseRepositoryPort | None = None,
        evaluation_service: PruefungService | None = None,
        settings_service: SettingsService | None = None,
        re_evaluation_service=None,
        notification_service=None,
        audit_service=None,
    ):
        self.claim_repository = claim_repository or ClaimRepository()
        self.settings_service = settings_service or SettingsService()
        self._evaluation_service = evaluation_service
        self.pruefung_service = evaluation_service
        self.income_repo = income_repository or IncomeRepository()
        self.expense_repo = expense_repository or ExpenseRepository()
        self.note_repo = ClaimNoteRepository()
        self._re_eval_svc = re_evaluation_service
        self._notification_svc = notification_service
        self._audit_svc = audit_service

    def _get_re_eval_svc(self):
        if self._re_eval_svc is None:
            from services.re_evaluation_service import ReEvaluationService
            self._re_eval_svc = ReEvaluationService()
        return self._re_eval_svc

    def _get_notification_svc(self):
        if self._notification_svc is None:
            from services.notification_service import NotificationService
            self._notification_svc = NotificationService()
        return self._notification_svc

    def _get_audit_svc(self):
        if self._audit_svc is None:
            from services.audit_service import AuditService
            self._audit_svc = AuditService()
        return self._audit_svc

    def _default_pruefung_service(self) -> PruefungService:
        return PruefungService(
            base_limit=self.settings_service.get("BASE_LIMIT"),
            additional_adult_limit=self.settings_service.get("ADDITIONAL_ADULT_LIMIT"),
            child_limit=self.settings_service.get("CHILD_LIMIT"),
            hardship_factor=self.settings_service.get("HARDSHIP_FACTOR"),
        )

    def _resolve_pruefung_service(self) -> PruefungService:
        if self._evaluation_service is not None:
            return self._evaluation_service

        return self._default_pruefung_service()

    def get_claim_by_id(self, claim_id: int) -> Optional[dict]:
        claim = self.claim_repository.get_claim_by_id(claim_id)
        if claim is None:
            return None

        claim["incomes"] = self.income_repo.get_incomes(claim_id)
        claim["expenses"] = self.expense_repo.get_expenses(claim_id)
        return claim

    def list_claims(
        self,
        location_id: int | None = None,
        status: str | None = None,
        statuses: list[str] | None = None,
        category_id: int | None = None,
        examiner_id: int | None = None,
        search_text: str | None = None,
        person_id: int | None = None,
    ) -> list[dict]:
        return self.claim_repository.get_claims(
            location_id=location_id,
            status=status,
            statuses=statuses,
            category_id=category_id,
            examiner_id=examiner_id,
            search_text=search_text,
            person_id=person_id,
        )

    def evaluate_claim(
        self,
        incomes: dict[str, float],
        expenses: dict[str, float],
        adult_count: int,
        child_count: int,
        category: str,
        disability_degree: Optional[int] = None,
        has_housing_benefit: Optional[bool] = None,
    ) -> dict:
        service = self._resolve_pruefung_service()
        result = service.evaluate_claim(
            incomes,
            expenses,
            adult_count,
            child_count,
            category,
            disability_degree,
            has_housing_benefit=has_housing_benefit,
        )
        return result.to_dict()

    def persist_evaluation(
        self,
        claim_id: int,
        incomes: Dict[str, float],
        expenses: Dict[str, dict],
        adult_count: int,
        child_count: int,
        category: str,
        disability_degree: Optional[int] = None,
        examiner_id: Optional[int] = None,
        has_housing_benefit: Optional[bool] = None,
    ) -> dict:
        # ── Prüfungssperre: Nur einmal pro Antrag für Mitarbeiter ─────────────
        re_eval_svc = self._get_re_eval_svc()
        eval_count = self.claim_repository.get_evaluation_count(claim_id)
        allowed, reason = re_eval_svc.can_evaluate(claim_id, eval_count)
        if not allowed:
            self._get_audit_svc().log(
                "evaluation_blocked", "claim", claim_id,
                f"Prüfversuch blockiert für User {examiner_id}. Grund: {reason}"
            )
            raise PermissionError(reason)

        is_first_evaluation = (eval_count == 0)

        self.income_repo.save_incomes(claim_id, incomes)
        self.expense_repo.save_expenses(claim_id, expenses)

        expense_amounts = {k: float(v.get("amount") or 0.0) for k, v in expenses.items()}

        service = self._resolve_pruefung_service()
        evaluation = service.evaluate_claim(
            incomes=incomes,
            expenses=expense_amounts,
            adult_count=adult_count,
            child_count=child_count,
            category=category,
            disability_degree=disability_degree,
            has_housing_benefit=has_housing_benefit,
        )

        evaluation_date = datetime.now(UTC).isoformat()

        self.claim_repository.update_claim_evaluation(
            claim_id=claim_id,
            status=evaluation.status,
            adult_count=adult_count,
            child_count=child_count,
            disability_degree=disability_degree,
            evaluation_reason=evaluation.reason,
            total_income=evaluation.total_income,
            total_expenses=evaluation.total_expenses,
            free_income=evaluation.free_income,
            entitlement_limit=evaluation.entitlement_limit,
            hardship_limit=evaluation.hardship_limit,
            evaluation_details=evaluation.details,
            examiner_id=examiner_id,
            evaluation_date=evaluation_date,
        )

        # ── Prüfungszähler inkrementieren ────────────────────────────────────
        self.claim_repository.increment_evaluation_count(
            claim_id, examiner_id, is_first=is_first_evaluation
        )

        # ── Bei Wiederholungsprüfung: genehmigte Freigabe verbrauchen ─────────
        if not is_first_evaluation:
            try:
                re_eval_svc.consume_approved_request(claim_id)
            except Exception:
                pass

        # ── Wohnbeihilfe-Status in Claim speichern ────────────────────────────
        if has_housing_benefit is not None:
            try:
                from database.db import get_connection
                with get_connection() as conn:
                    conn.execute(
                        "UPDATE claims SET has_housing_benefit=? WHERE id=?",
                        (1 if has_housing_benefit else 0, claim_id),
                    )
                    conn.commit()
            except Exception:
                pass

        # ── AuditLog ──────────────────────────────────────────────────────────
        from core.claim_status import ClaimStatus
        status_display = ClaimStatus.get_display(evaluation.status)
        audit_action = "first_evaluation_completed" if is_first_evaluation else "re_evaluation_completed"
        self._get_audit_svc().log(
            audit_action, "claim", claim_id,
            f"Prüfer: {examiner_id} | Status: {status_display} | "
            f"Erstprüfung: {'Ja' if is_first_evaluation else 'Nein'}"
        )

        # ── Nach Erstprüfung: Supervisor benachrichtigen ───────────────────────
        if is_first_evaluation:
            try:
                claim = self.claim_repository.get_claim_by_id(claim_id)
                case_number   = (claim or {}).get("case_number", str(claim_id))
                examiner_name = (claim or {}).get("examiner_name", f"User {examiner_id}")
                self._get_notification_svc().notify_supervisors_first_evaluation_done(
                    case_number=case_number,
                    claim_id=claim_id,
                    examiner_name=examiner_name,
                    status_display=status_display,
                    evaluation_date=evaluation_date,
                )
                self._get_audit_svc().log(
                    "supervisor_notified_after_first_evaluation", "claim", claim_id,
                    f"Supervisor benachrichtigt nach Erstprüfung von {case_number}."
                )
            except Exception:
                pass

        return evaluation.to_dict()

    def update_claim_status(self, claim_id: int, status: str, note: str | None = None) -> bool:
        if not ClaimStatus.is_valid_status(status):
            return False

        old = self.claim_repository.get_claim_by_id(claim_id)
        old_status = old["status"] if old else None

        result = self.claim_repository.update_claim_status(claim_id, status)
        if result:
            try:
                self.claim_repository.record_claim_history(
                    claim_id=claim_id,
                    new_status=status,
                    old_status=old_status,
                    changed_by=Session.get_user_id(),
                    note=note,
                )
            except Exception:
                pass
        return result

    def set_review_date(self, claim_id: int, review_date: Optional[str]) -> bool:
        return self.claim_repository.update_review_date(claim_id, review_date)

    def get_claim_history(self, claim_id: int) -> List[dict]:
        return self.claim_repository.get_claim_history(claim_id)

    def clone_claim(self, claim_id: int, created_by: Optional[int] = None) -> Optional[dict]:
        source = self.claim_repository.get_claim_by_id(claim_id)
        if not source:
            return None

        created_by = created_by or Session.get_user_id() or source.get("user_id", 1)
        year = datetime.now(UTC).year
        prefix = "AS"
        try:
            prefix = str(self.settings_service.get("CASE_NUMBER_PREFIX", "AS") or "AS")
        except Exception:
            pass

        new_case_number = self.claim_repository.generate_next_case_number(year, prefix)
        new_id = self.claim_repository.create_claim(
            case_number=new_case_number,
            person_id=source.get("person_id"),
            user_id=created_by,
            location_id=source["location_id"],
            category_id=source.get("category_id"),
            description=source["description"],
            start_date=source.get("start_date"),
            end_date=source.get("end_date"),
            adult_count=source.get("adult_count") or 1,
            child_count=source.get("child_count") or 0,
            disability_degree=source.get("disability_degree"),
            created_by=created_by,
        )
        try:
            self.claim_repository.record_claim_history(
                claim_id=new_id,
                new_status=ClaimStatus.IN_PRUEFUNG,
                old_status=None,
                changed_by=created_by,
                note=f"Klon von Fall {source.get('case_number', claim_id)}",
            )
        except Exception:
            pass
        return {"id": new_id, "case_number": new_case_number}

    # ── Interne Notizen ──────────────────────────────────────────────────────
    def add_claim_note(self, claim_id: int, text: str) -> int | None:
        return self.note_repo.add_note(claim_id, Session.get_user_id(), text)

    def get_claim_notes(self, claim_id: int) -> List[dict]:
        return self.note_repo.get_notes(claim_id)

    def delete_claim_note(self, note_id: int) -> bool:
        return self.note_repo.delete_note(note_id)

    # ── Aktivitäts-Feed ──────────────────────────────────────────────────────
    def get_activity_feed(self, claim_id: int) -> List[dict]:
        events: List[dict] = []
        for entry in self.claim_repository.get_claim_history(claim_id):
            events.append({
                "type": "status",
                "timestamp": entry.get("changed_at", ""),
                "author": entry.get("changed_by_name") or "System",
                "text": f"{ClaimStatus.get_display(entry.get('old_status') or '') or '–'} → {ClaimStatus.get_display(entry.get('new_status') or '') or '?'}",
                "detail": entry.get("note") or "",
            })
        for note in self.note_repo.get_notes(claim_id):
            events.append({
                "type": "note",
                "timestamp": note.get("created_at", ""),
                "author": note.get("author_name") or "–",
                "text": note.get("note_text", ""),
                "detail": "",
            })
        events.sort(key=lambda e: e["timestamp"])
        return events

    # ── Widerspruch ───────────────────────────────────────────────────────────
    def set_widerspruch(self, claim_id: int, frist: str | None) -> bool:
        ok = self.claim_repository.set_widerspruch_frist(claim_id, frist)
        if ok:
            self.update_claim_status(claim_id, ClaimStatus.WIDERSPRUCH,
                                     note=f"Widerspruch eingelegt, Frist: {frist or '–'}")
        return ok

    # ── Warteliste ────────────────────────────────────────────────────────────
    def get_waitlist(self, location_id: int | None = None) -> List[dict]:
        return self.claim_repository.get_waitlist_claims(location_id)

    def get_claim_statuses(self) -> list[str]:
        return ClaimStatus.ALL_STATUSES

    def count_claims(
        self,
        status: str | None = None,
        statuses: list[str] | None = None,
        location_id: int | None = None,
        category_id: int | None = None,
        examiner_id: int | None = None,
        start_date: str | None = None,
        created_since_days: int | None = None,
    ) -> int:
        return self.claim_repository.count_claims(
            status=status,
            statuses=statuses,
            location_id=location_id,
            category_id=category_id,
            examiner_id=examiner_id,
            start_date=start_date,
            created_since_days=created_since_days,
        )

    def get_valid_categories(self) -> list[str]:
        return self._resolve_pruefung_service().get_valid_categories()

    def get_allowed_transitions(self, current_status: str, role_name: str) -> list[str]:
        return ClaimStatus.get_allowed_transitions(current_status, role_name)
