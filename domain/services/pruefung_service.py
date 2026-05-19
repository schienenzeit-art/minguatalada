from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.claim_status import ClaimStatus
from domain.categories import CATEGORIES


@dataclass
class EvaluationResult:
    status: str
    is_eligible: bool
    is_hardship: bool
    has_disability_rejection: bool
    total_income: float
    total_expenses: float
    free_income: float
    entitlement_limit: float
    hardship_limit: float
    category: str
    disability_degree: Optional[int]
    reason: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "is_eligible": self.is_eligible,
            "is_hardship": self.is_hardship,
            "has_disability_rejection": self.has_disability_rejection,
            "total_income": self.total_income,
            "total_expenses": self.total_expenses,
            "free_income": self.free_income,
            "entitlement_limit": self.entitlement_limit,
            "hardship_limit": self.hardship_limit,
            "category": self.category,
            "disability_degree": self.disability_degree,
            "reason": self.reason,
            "details": self.details,
        }


class PruefungService:
    BASE_LIMIT = 820.0
    ADDITIONAL_ADULT_LIMIT = 390.0
    CHILD_LIMIT = 185.0
    HARDSHIP_FACTOR = 1.1

    def __init__(
        self,
        base_limit: float | None = None,
        additional_adult_limit: float | None = None,
        child_limit: float | None = None,
        hardship_factor: float | None = None,
    ):
        # instance-level configurable thresholds; fall back to class defaults
        self.base_limit = base_limit if base_limit is not None else self.BASE_LIMIT
        self.additional_adult_limit = (
            additional_adult_limit
            if additional_adult_limit is not None
            else self.ADDITIONAL_ADULT_LIMIT
        )
        self.child_limit = child_limit if child_limit is not None else self.CHILD_LIMIT
        self.hardship_factor = hardship_factor if hardship_factor is not None else self.HARDSHIP_FACTOR

    def evaluate_claim(
        self,
        incomes: Dict[str, float],
        expenses: Dict[str, float],
        adult_count: int,
        child_count: int,
        category: str,
        disability_degree: Optional[int] = None,
    ) -> EvaluationResult:
        incomes = self._normalize_amounts(incomes)
        expenses = self._normalize_amounts(expenses)

        total_income = sum(incomes.values())
        total_expenses = sum(expenses.values())
        free_income = total_income - total_expenses

        additional_adults = max(adult_count - 1, 0)
        entitlement_limit = (
            self.base_limit
            + self.additional_adult_limit * additional_adults
            + self.child_limit * child_count
        )
        hardship_limit = round(entitlement_limit * self.hardship_factor, 2)

        has_disability_rejection = (
            category == "Menschen mit Beeinträchtigung"
            and disability_degree is not None
            and disability_degree < 60
        )

        if has_disability_rejection:
            status = ClaimStatus.ABGELEHNT
            reason = (
                "Kategorie 'Menschen mit Beeinträchtigung' und "
                f"Behinderungsgrad {disability_degree}% unter 60% führen zur Ablehnung."
            )
        elif free_income <= entitlement_limit:
            status = ClaimStatus.ANSPRUCHSBERECHTIGT
            reason = "Frei verfügbares Einkommen liegt unter oder gleich der Anspruchsgrenze."
        elif free_income <= hardship_limit:
            status = ClaimStatus.HAERTEFALL
            reason = "Frei verfügbares Einkommen liegt im Härtefallbereich."
        else:
            status = ClaimStatus.ABGELEHNT
            reason = "Frei verfügbares Einkommen liegt über der Härtefallgrenze."

        details = {
            "incomes": incomes,
            "expenses": expenses,
            "additional_adults": additional_adults,
            "child_count": child_count,
        }

        return EvaluationResult(
            status=status,
            is_eligible=status == ClaimStatus.ANSPRUCHSBERECHTIGT,
            is_hardship=status == ClaimStatus.HAERTEFALL,
            has_disability_rejection=has_disability_rejection,
            total_income=total_income,
            total_expenses=total_expenses,
            free_income=free_income,
            entitlement_limit=entitlement_limit,
            hardship_limit=hardship_limit,
            category=category,
            disability_degree=disability_degree,
            reason=reason,
            details=details,
        )

    def get_valid_categories(self) -> list[str]:
        return list(CATEGORIES)

    def _normalize_amounts(self, values: Dict[str, float]) -> Dict[str, float]:
        normalized: Dict[str, float] = {}
        for key, raw_value in values.items():
            normalized[key] = max(float(raw_value or 0), 0.0)
        return normalized
