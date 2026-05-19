from __future__ import annotations

from typing import Protocol, Optional, List, Dict, Any


class UserRepositoryPort(Protocol):
    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        ...

    def get_all(self) -> List[Dict[str, Any]]:
        ...

    def get_roles(self) -> List[Dict[str, Any]]:
        ...

    def get_locations(self) -> List[Dict[str, Any]]:
        ...

    def get_users_by_location_id(self, location_id: int | None = None) -> List[Dict[str, Any]]:
        ...

    def create(
        self,
        full_name: str,
        username: str,
        password_hash: str,
        role_id: int,
        location_id: int | None,
        is_active: bool,
    ) -> None:
        ...

    def set_active(self, user_id: int, is_active: bool) -> None:
        ...

    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        ...

    def update_user(
        self,
        user_id: int,
        full_name: str,
        username: str,
        role_id: int,
        location_id: int | None,
        is_active: bool,
        password_hash: str | None = None,
    ) -> bool:
        ...


class LocationRepositoryPort(Protocol):
    def list_locations(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        ...

    def get_location_by_id(self, location_id: int) -> Optional[Dict[str, Any]]:
        ...


class CategoryRepositoryPort(Protocol):
    def list_categories(self) -> List[Dict[str, Any]]:
        ...


class PersonRepositoryPort(Protocol):
    def create_person(self, person: Dict[str, Any]) -> int:
        ...


class CaseRepositoryPort(Protocol):
    def create_case(
        self,
        case_number: str,
        person_id: int,
        user_id: int,
        location_id: int,
        category_id: int | None,
        description: str,
        start_date: str | None = None,
        end_date: str | None = None,
        created_by: int | None = None,
    ) -> int:
        ...

    def get_last_case_number_for_year(self, year: int) -> Optional[str]:
        ...


class ClaimRepositoryPort(Protocol):
    def get_claim_by_id(self, claim_id: int) -> Optional[Dict[str, Any]]:
        ...

    def update_claim_status(self, claim_id: int, status: str) -> bool:
        ...

    def get_claims(
        self,
        location_id: int | None = None,
        status: str | None = None,
        category_id: int | None = None,
        examiner_id: int | None = None,
        search_text: str | None = None,
    ) -> List[Dict[str, Any]]:
        ...

    def update_claim_evaluation(
        self,
        claim_id: int,
        status: str | None = None,
        adult_count: int | None = None,
        child_count: int | None = None,
        disability_degree: int | None = None,
        evaluation_reason: str | None = None,
        total_income: float | None = None,
        total_expenses: float | None = None,
        free_income: float | None = None,
        entitlement_limit: float | None = None,
        hardship_limit: float | None = None,
        evaluation_details: dict | None = None,
        examiner_id: int | None = None,
        evaluation_date: str | None = None,
    ) -> bool:
        ...


class IncomeRepositoryPort(Protocol):
    def get_incomes(self, claim_id: int) -> List[Dict[str, Any]]:
        ...

    def save_incomes(self, claim_id: int, incomes: Dict[str, float]) -> None:
        ...


class ExpenseRepositoryPort(Protocol):
    def get_expenses(self, claim_id: int) -> List[Dict[str, Any]]:
        ...

    def save_expenses(self, claim_id: int, expenses: Dict[str, Dict[str, Any]]) -> None:
        ...
