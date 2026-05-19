import unittest

from services.pruefung_service import PruefungService
from core.claim_status import ClaimStatus


class PruefungServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = PruefungService()

    def test_anspruchsberechtigt_when_income_below_limit(self):
        result = self.service.evaluate_claim(
            incomes={"Gehalt": 1000.0},
            expenses={"Miete": 300.0, "Strom": 50.0},
            adult_count=1,
            child_count=1,
            category="Pensionist",
        )

        self.assertEqual(result.status, ClaimStatus.ANSPRUCHSBERECHTIGT)
        self.assertTrue(result.is_eligible)
        self.assertFalse(result.is_hardship)
        self.assertFalse(result.has_disability_rejection)

    def test_haerterfall_when_income_between_limit_and_hardship(self):
        result = self.service.evaluate_claim(
            incomes={"Gehalt": 1700.0},
            expenses={"Miete": 500.0, "Strom": 100.0},
            adult_count=1,
            child_count=1,
            category="Alleinerziehend",
        )

        self.assertEqual(result.status, ClaimStatus.HAERTEFALL)
        self.assertFalse(result.is_eligible)
        self.assertTrue(result.is_hardship)

    def test_abgelehnt_when_income_above_hardship_limit(self):
        result = self.service.evaluate_claim(
            incomes={"Gehalt": 2500.0},
            expenses={"Miete": 300.0, "Strom": 150.0},
            adult_count=1,
            child_count=0,
            category="Pensionist",
        )

        self.assertEqual(result.status, ClaimStatus.ABGELEHNT)
        self.assertFalse(result.is_eligible)
        self.assertFalse(result.is_hardship)

    def test_abgelehnt_when_disability_degree_under_60(self):
        result = self.service.evaluate_claim(
            incomes={"Gehalt": 1000.0},
            expenses={"Miete": 100.0},
            adult_count=1,
            child_count=0,
            category="Menschen mit Beeinträchtigung",
            disability_degree=50,
        )

        self.assertEqual(result.status, ClaimStatus.ABGELEHNT)
        self.assertTrue(result.has_disability_rejection)
        self.assertEqual(
            result.reason,
            "Kategorie 'Menschen mit Beeinträchtigung' und Behinderungsgrad 50% unter 60% führen zur Ablehnung."
        )


if __name__ == "__main__":
    unittest.main()
