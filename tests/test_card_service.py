import unittest
from unittest.mock import MagicMock

from services.card_service import CardService
from core.claim_status import ClaimStatus
from core.card_status import CardStatus


class CardServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = CardService()
        self.service.claim_repository = MagicMock()
        self.service.card_repository = MagicMock()

    def test_can_create_card_for_claim_when_eligible(self):
        self.service.claim_repository.get_claim_by_id.return_value = {
            "id": 1,
            "status": ClaimStatus.ANSPRUCHSBERECHTIGT,
            "person_id": 10,
            "location_id": 2,
        }
        self.service.card_repository.get_cards_by_claim.return_value = []

        allowed, reason = self.service.can_create_card_for_claim(1)

        self.assertTrue(allowed)
        self.assertEqual(reason, "")

    def test_can_create_card_for_claim_rejects_abgelehnt(self):
        self.service.claim_repository.get_claim_by_id.return_value = {
            "id": 1,
            "status": ClaimStatus.ABGELEHNT,
            "person_id": 10,
            "location_id": 2,
        }

        allowed, reason = self.service.can_create_card_for_claim(1)

        self.assertFalse(allowed)
        self.assertIn("abgelehnten Fall", reason)

    def test_create_card_generates_card_number_and_returns_card(self):
        self.service.claim_repository.get_claim_by_id.return_value = {
            "id": 1,
            "status": ClaimStatus.ANSPRUCHSBERECHTIGT,
            "person_id": 10,
            "location_id": 2,
        }
        self.service.card_repository.get_cards_by_claim.return_value = []
        self.service.card_repository.get_next_card_number.return_value = "K-2026-000001"
        self.service.card_repository.create_card.return_value = 123
        self.service.card_repository.get_card_by_id.return_value = {
            "id": 123,
            "card_number": "K-2026-000001",
        }

        card = self.service.create_card(claim_id=1, created_by=5)

        self.assertIsNotNone(card)
        self.assertEqual(card["card_number"], "K-2026-000001")
        self.service.card_repository.create_card.assert_called_once()

    def test_get_all_card_statuses_returns_the_expected_statuses(self):
        self.assertListEqual(self.service.get_all_card_statuses(), CardStatus.ALL_STATUSES)


if __name__ == "__main__":
    unittest.main()
