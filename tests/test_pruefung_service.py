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
            has_housing_benefit=True,
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
            has_housing_benefit=True,
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
            has_housing_benefit=True,
        )
        self.assertEqual(result.status, ClaimStatus.ABGELEHNT)
        self.assertFalse(result.is_eligible)
        self.assertFalse(result.is_hardship)

    def test_no_housing_benefit_triggers_vorlaefig_abgelehnt(self):
        """Fehlende Wohnbeihilfe führt zu vorläufiger Ablehnung (auch wenn Einkommen passt)."""
        result = self.service.evaluate_claim(
            incomes={"Gehalt": 1000.0},
            expenses={"Miete": 300.0},
            adult_count=1,
            child_count=0,
            category="Pensionist",
            has_housing_benefit=False,
        )
        self.assertEqual(result.status, ClaimStatus.VORLAEFIG_ABGELEHNT)
        self.assertTrue(result.has_no_housing_benefit)

    def test_unset_housing_benefit_triggers_vorlaefig_abgelehnt(self):
        """Nicht angegebene Wohnbeihilfe (None) gilt ebenfalls als fehlend."""
        result = self.service.evaluate_claim(
            incomes={"Gehalt": 1000.0},
            expenses={"Miete": 300.0},
            adult_count=1,
            child_count=0,
            category="Pensionist",
            has_housing_benefit=None,
        )
        self.assertEqual(result.status, ClaimStatus.VORLAEFIG_ABGELEHNT)

    def test_disability_degree_no_longer_causes_rejection(self):
        """Behinderungsgrad unter 60% führt nicht mehr zur Ablehnung (Anforderung geändert)."""
        result = self.service.evaluate_claim(
            incomes={"Gehalt": 500.0},
            expenses={"Miete": 100.0},
            adult_count=1,
            child_count=0,
            category="Menschen mit Beeinträchtigung",
            disability_degree=50,
            has_housing_benefit=True,
        )
        self.assertEqual(result.status, ClaimStatus.ANSPRUCHSBERECHTIGT)
        self.assertFalse(result.has_disability_rejection)

    def test_multiple_adults_increase_limit(self):
        """Jeder weitere Erwachsene erhöht die Anspruchsgrenze um ADDITIONAL_ADULT_LIMIT."""
        single = self.service.evaluate_claim(
            incomes={}, expenses={}, adult_count=1, child_count=0,
            category="Pensionist", has_housing_benefit=True,
        )
        couple = self.service.evaluate_claim(
            incomes={}, expenses={}, adult_count=2, child_count=0,
            category="Pensionist", has_housing_benefit=True,
        )
        self.assertAlmostEqual(
            couple.entitlement_limit - single.entitlement_limit,
            PruefungService.ADDITIONAL_ADULT_LIMIT,
        )

    def test_children_increase_limit(self):
        """Jedes Kind erhöht die Anspruchsgrenze um CHILD_LIMIT."""
        no_kids = self.service.evaluate_claim(
            incomes={}, expenses={}, adult_count=1, child_count=0,
            category="Familie", has_housing_benefit=True,
        )
        with_kid = self.service.evaluate_claim(
            incomes={}, expenses={}, adult_count=1, child_count=1,
            category="Familie", has_housing_benefit=True,
        )
        self.assertAlmostEqual(
            with_kid.entitlement_limit - no_kids.entitlement_limit,
            PruefungService.CHILD_LIMIT,
        )


if __name__ == "__main__":
    unittest.main()
