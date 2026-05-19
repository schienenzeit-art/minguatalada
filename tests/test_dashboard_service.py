import unittest
from unittest.mock import MagicMock

from services.dashboard_service import DashboardService


class DashboardServiceTest(unittest.TestCase):
    def setUp(self):
        self.claim_service = MagicMock()
        self.card_service = MagicMock()
        self.location_service = MagicMock()
        self.dashboard_service = DashboardService(
            claim_service=self.claim_service,
            card_service=self.card_service,
            location_service=self.location_service,
        )

    def test_get_kpi_items_returns_clickable_metrics(self):
        self.claim_service.count_claims.side_effect = [5, 12, 8, 3, 7, 2]
        self.card_service.count_cards.return_value = 11
        self.card_service.count_expiring_cards.return_value = 4
        self.location_service.list_active_locations.return_value = [{}, {}, {}]

        kpis = self.dashboard_service.get_kpi_items()
        summary = self.dashboard_service.get_summary_items()

        self.assertEqual(len(kpis), 4)
        self.assertEqual(kpis[0]["title"], "Offene Ansprüche")
        self.assertEqual(kpis[0]["page"], "claims")
        self.assertEqual(kpis[1]["title"], "Laufende Karten")
        self.assertEqual(kpis[1]["page"], "cards")
        self.assertEqual(kpis[2]["title"], "Genehmigte Fälle")
        self.assertEqual(kpis[3]["title"], "Abgelehnte Fälle")
        self.assertEqual(summary[1]["title"], "Karten in 30 Tagen ablaufend")
        self.assertEqual(summary[1]["value"], "4")
        self.assertEqual(summary[3]["value"], "3")

        self.card_service.count_cards.assert_called_once()
        self.card_service.count_expiring_cards.assert_called_once()
        self.location_service.list_active_locations.assert_called_once()

    def test_dashboard_items_use_correct_claim_filters(self):
        self.claim_service.count_claims.side_effect = [5, 8, 3, 1, 2, 4]
        self.card_service.count_cards.return_value = 10
        self.card_service.count_expiring_cards.return_value = 1
        self.location_service.list_active_locations.return_value = []

        self.dashboard_service.get_kpi_items()
        self.dashboard_service.get_summary_items()

        self.claim_service.count_claims.assert_any_call(status="IN_PRUEFUNG")
        self.claim_service.count_claims.assert_any_call(statuses=["ANSPRUCHSBERECHTIGT", "HAERTEFALL"])
        self.claim_service.count_claims.assert_any_call(status="ABGELEHNT")
        self.claim_service.count_claims.assert_any_call(start_date=unittest.mock.ANY)
        self.claim_service.count_claims.assert_any_call(created_since_days=7)


if __name__ == "__main__":
    unittest.main()
