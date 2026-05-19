import unittest

from database.db import initialize_database
from services.auth_service import AuthService


class AuthServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()
        cls.service = AuthService()

    def test_admin_login_success(self):
        result = self.service.login("admin", "admin123")
        self.assertTrue(result["success"])
        self.assertEqual(result["user"]["username"], "admin")

    def test_invalid_login_failure(self):
        result = self.service.login("admin", "wrongpass")
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Passwort ist falsch.")

    def test_missing_username_or_password(self):
        result = self.service.login("", "")
        self.assertFalse(result["success"])
        self.assertIn("Benutzername und Passwort", result["message"])


if __name__ == "__main__":
    unittest.main()
