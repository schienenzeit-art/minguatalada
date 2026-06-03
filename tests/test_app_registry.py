import unittest
from unittest.mock import patch

from app.app_registry import AppRegistry


class AppRegistryTest(unittest.TestCase):
    def test_get_visible_apps_for_regular_user(self):
        # Mitarbeiter hat keine privilegierten Rechte → kein Verwaltungsbereich
        with patch("app.app_registry.Session.get_user", return_value={"role_name": "Mitarbeiter"}):
            visible_apps = AppRegistry.get_visible_apps()
            self.assertTrue(any(app.id == "anspruchspruefung" for app in visible_apps))
            self.assertTrue(any(app.id == "aufgaben" for app in visible_apps))
            self.assertFalse(any(app.id == "administration" for app in visible_apps))

    def test_get_visible_apps_for_admin_user(self):
        # Admin sieht alle Apps inklusive Verwaltung
        with patch("app.app_registry.Session.get_user", return_value={"role_name": "Admin"}):
            visible_apps = AppRegistry.get_visible_apps()
            self.assertTrue(any(app.id == "anspruchspruefung" for app in visible_apps))
            self.assertTrue(any(app.id == "administration" for app in visible_apps))

    def test_get_visible_apps_for_supervisor(self):
        # Supervisor hat ebenfalls privilegierte Rechte
        with patch("app.app_registry.Session.get_user", return_value={"role_name": "Supervisor"}):
            visible_apps = AppRegistry.get_visible_apps()
            self.assertTrue(any(app.id == "administration" for app in visible_apps))


if __name__ == "__main__":
    unittest.main()
