import unittest

from core.session import Session
from services.settings_service import SettingsService
from services.claim_service import ClaimService
from core.claim_status import ClaimStatus


class SettingsServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = SettingsService()
        Session.set_user({"id": 1, "role_name": "Admin"})

    def tearDown(self):
        Session.clear()

    def test_get_all_settings_returns_seeded_defaults(self):
        settings = self.service.get_all_settings()
        self.assertTrue(any(s["key"] == "BASE_LIMIT" for s in settings))
        self.assertTrue(any(s["key"] == "CHILD_LIMIT" for s in settings))

    def test_update_setting_requires_admin(self):
        Session.set_user({"id": 2, "role_name": "Mitarbeiter"})
        with self.assertRaises(PermissionError):
            self.service.update_setting("BASE_LIMIT", 900.0, comment="Test")

    def test_update_setting_records_audit_and_value(self):
        old_setting = self.service.get_setting("BASE_LIMIT")
        self.assertIsNotNone(old_setting)

        updated = self.service.update_setting("BASE_LIMIT", 999.0, comment="Anpassung für Test")
        self.assertEqual(updated["value"], 999.0)

        refreshed = self.service.get_setting("BASE_LIMIT")
        self.assertEqual(refreshed["value"], 999.0)

        # restore original value for other tests
        self.service.update_setting("BASE_LIMIT", old_setting["value"], comment="Restore")


class ClaimServiceSettingsTest(unittest.TestCase):
    def setUp(self):
        self.settings_service = SettingsService()
        self.claim_service = ClaimService(settings_service=self.settings_service)
        Session.set_user({"id": 1, "role_name": "Admin"})

    def tearDown(self):
        Session.clear()

    def test_evaluation_uses_updated_settings(self):
        original_setting = self.settings_service.get_setting("BASE_LIMIT")
        self.assertIsNotNone(original_setting)

        try:
            self.settings_service.update_setting("BASE_LIMIT", 1000.0, comment="Test override")
            result = self.claim_service.evaluate_claim(
                incomes={"Gehalt": 1000.0},
                expenses={"Miete": 0.0},
                adult_count=1,
                child_count=0,
                category="Pensionist",
            )
            self.assertEqual(result["entitlement_limit"], 1000.0)
        finally:
            self.settings_service.update_setting(
                "BASE_LIMIT",
                original_setting["value"],
                comment="Restore",
            )


if __name__ == "__main__":
    unittest.main()
