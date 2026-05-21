from datetime import datetime
from typing import Optional, Dict

from app.ports import ClaimRepositoryPort, ExpenseRepositoryPort, IncomeRepositoryPort
from core.claim_status import ClaimStatus
from database.repositories.claim_repository import ClaimRepository
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
    ):
        self.claim_repository = claim_repository or ClaimRepository()
        self.settings_service = settings_service or SettingsService()
        self._evaluation_service = evaluation_service
        self.pruefung_service = evaluation_service
        self.income_repo = income_repository or IncomeRepository()
        self.expense_repo = expense_repository or ExpenseRepository()

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
        category_id: int | None = None,
        examiner_id: int | None = None,
        search_text: str | None = None,
        person_id: int | None = None,
    ) -> list[dict]:
        return self.claim_repository.get_claims(
            location_id=location_id,
            status=status,
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
    ) -> dict:
        service = self._resolve_pruefung_service()
        result = service.evaluate_claim(
            incomes,
            expenses,
            adult_count,
            child_count,
            category,
            disability_degree,
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
    ) -> dict:
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
        )

        evaluation_date = datetime.utcnow().isoformat()

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

        return evaluation.to_dict()

    def update_claim_status(self, claim_id: int, status: str) -> bool:
        if not ClaimStatus.is_valid_status(status):
            return False

        return self.claim_repository.update_claim_status(claim_id, status)

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
