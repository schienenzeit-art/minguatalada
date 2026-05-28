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
    has_no_housing_benefit: bool
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
            "has_no_housing_benefit": self.has_no_housing_benefit,
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
        has_housing_benefit: Optional[bool] = None,
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

        # Beeinträchtigung: Mindestprozente entfallen – kein automatischer Ablehnungsgrund mehr
        has_disability_rejection = False

        # Einkommensbasierte Beurteilung
        if free_income <= entitlement_limit:
            base_status = ClaimStatus.ANSPRUCHSBERECHTIGT
            base_reason = "Frei verfügbares Einkommen liegt unter oder gleich der Anspruchsgrenze."
        elif free_income <= hardship_limit:
            base_status = ClaimStatus.HAERTEFALL
            base_reason = "Frei verfügbares Einkommen liegt im Härtefallbereich."
        else:
            base_status = ClaimStatus.ABGELEHNT
            base_reason = "Frei verfügbares Einkommen liegt über der Härtefallgrenze."

        # Wohnbeihilfe-Prüfung: fehlt → vorläufig abgelehnt (weitere Abklärung nötig)
        # Gilt nur wenn der Fall ansonsten anspruchsberechtigt oder Härtefall wäre
        has_no_housing_benefit = has_housing_benefit is False or (has_housing_benefit is None and False)
        # has_housing_benefit=None bedeutet "nicht angegeben" → als fehlend werten
        if has_housing_benefit is None:
            has_no_housing_benefit = True

        if has_no_housing_benefit and base_status in [
            ClaimStatus.ANSPRUCHSBERECHTIGT,
            ClaimStatus.HAERTEFALL,
        ]:
            status = ClaimStatus.VORLAEFIG_ABGELEHNT
            reason = (
                "Keine Wohnbeihilfe angegeben. "
                "Vorläufig abgelehnt – weitere Abklärungen notwendig. "
                "Einkommenstechnisch wäre: " + base_reason
            )
        elif has_no_housing_benefit and base_status == ClaimStatus.ABGELEHNT:
            status = ClaimStatus.ABGELEHNT
            reason = base_reason + " Zusätzlich: Keine Wohnbeihilfe angegeben."
        else:
            status = base_status
            reason = base_reason

        details = {
            "incomes": incomes,
            "expenses": expenses,
            "additional_adults": additional_adults,
            "child_count": child_count,
            "has_housing_benefit": has_housing_benefit,
        }

        return EvaluationResult(
            status=status,
            is_eligible=status == ClaimStatus.ANSPRUCHSBERECHTIGT,
            is_hardship=status == ClaimStatus.HAERTEFALL,
            has_disability_rejection=has_disability_rejection,
            has_no_housing_benefit=has_no_housing_benefit,
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
