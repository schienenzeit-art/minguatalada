from typing import List, Dict, Optional

from database.repositories.person_repository import PersonRepository


class PersonService:
    NO_CLAIM_STATUS = "KEIN_FALL"

    def __init__(
        self,
        person_repository: PersonRepository | None = None,
    ):
        self.person_repository = person_repository or PersonRepository()

    def list_persons(
        self,
        last_name: str | None = None,
        first_name: str | None = None,
        location_id: int | None = None,
        status: str | None = None,
    ) -> List[Dict[str, object]]:
        return self.person_repository.list_persons(
            last_name=last_name,
            first_name=first_name,
            location_id=location_id,
            latest_claim_status=status,
        )

    def get_person_by_id(self, person_id: int) -> Optional[Dict[str, object]]:
        return self.person_repository.get_person_by_id(person_id)
