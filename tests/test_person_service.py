import unittest
from unittest.mock import MagicMock

from services.person_service import PersonService


class PersonServiceTest(unittest.TestCase):
    def setUp(self):
        self.person_repository = MagicMock()
        self.person_service = PersonService(person_repository=self.person_repository)

    def test_list_persons_calls_repository_with_filters(self):
        self.person_repository.list_persons.return_value = [
            {"id": 1, "first_name": "Anna", "last_name": "Müller"}
        ]

        result = self.person_service.list_persons(
            last_name="Müller",
            first_name="Anna",
            location_id=3,
            status="IN_PRUEFUNG",
        )

        self.person_repository.list_persons.assert_called_once_with(
            last_name="Müller",
            first_name="Anna",
            location_id=3,
            latest_claim_status="IN_PRUEFUNG",
        )
        self.assertEqual(result, [{"id": 1, "first_name": "Anna", "last_name": "Müller"}])

    def test_get_person_by_id_returns_person(self):
        self.person_repository.get_person_by_id.return_value = {"id": 42, "first_name": "Max"}

        result = self.person_service.get_person_by_id(42)

        self.person_repository.get_person_by_id.assert_called_once_with(42)
        self.assertEqual(result, {"id": 42, "first_name": "Max"})


if __name__ == "__main__":
    unittest.main()
