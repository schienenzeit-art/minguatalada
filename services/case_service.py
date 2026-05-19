from datetime import datetime
from typing import Dict, Optional

from app.ports import CaseRepositoryPort, CategoryRepositoryPort, LocationRepositoryPort, PersonRepositoryPort
from database.repositories.case_repository import CaseRepository
from database.repositories.category_repository import CategoryRepository
from database.repositories.location_repository import LocationRepository
from database.repositories.person_repository import PersonRepository


class CaseService:
    def __init__(
        self,
        person_repo: PersonRepositoryPort | None = None,
        case_repo: CaseRepositoryPort | None = None,
        location_repo: LocationRepositoryPort | None = None,
        category_repo: CategoryRepositoryPort | None = None,
    ) -> None:
        self.person_repo = person_repo or PersonRepository()
        self.case_repo = case_repo or CaseRepository()
        self.location_repo = location_repo or LocationRepository()
        self.category_repo = category_repo or CategoryRepository()

    def generate_case_number(self) -> str:
        year = datetime.utcnow().year
        last_case_number = self.case_repo.get_last_case_number_for_year(year)

        if last_case_number:
            try:
                last_seq = int(last_case_number.split("-")[-1])
            except Exception:
                last_seq = 0
        else:
            last_seq = 0

        next_seq = last_seq + 1
        return f"AS-{year}-{next_seq:06d}"

    def list_categories(self) -> list[dict]:
        return self.category_repo.list_categories()

    def list_locations(self, include_inactive: bool = False) -> list[dict]:
        return self.location_repo.list_locations(include_inactive=include_inactive)

    def create_case(
        self,
        person: Dict[str, object],
        category_id: Optional[int],
        location_id: int,
        description: str = "Neuer Antrag",
        created_by: Optional[int] = None,
    ) -> Dict[str, object]:
        person_id = self.person_repo.create_person(person)
        user_id = created_by or 1
        case_number = self.generate_case_number()

        case_id = self.case_repo.create_case(
            case_number=case_number,
            person_id=person_id,
            user_id=user_id,
            location_id=location_id,
            category_id=category_id,
            description=description,
            created_by=user_id,
        )

        return {
            "id": case_id,
            "case_number": case_number,
            "person_id": person_id,
        }
