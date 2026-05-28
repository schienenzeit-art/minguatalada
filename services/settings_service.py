"""Database-backed settings storage for admin-configurable thresholds.

The settings table stores all configurable parameters and supports audit
recording for changes made by administrators.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from core.session import Session
from database.db import initialize_database, get_connection
from database.repositories.setting_repository import SettingRepository


DEFAULT_SETTINGS = {
    # ── SMTP-Konfiguration ────────────────────────────────────────────────────
    "SMTP_HOST": {
        "value": "", "value_type": "text", "category": "E-Mail",
        "description": "SMTP-Servername (z. B. smtp.office365.com)",
        "editable_by_admin": True,
    },
    "SMTP_PORT": {
        "value": 587, "value_type": "number", "category": "E-Mail",
        "description": "SMTP-Port (587 für TLS, 465 für SSL)",
        "editable_by_admin": True,
    },
    "SMTP_USER": {
        "value": "", "value_type": "text", "category": "E-Mail",
        "description": "SMTP-Benutzername / E-Mail-Adresse",
        "editable_by_admin": True,
    },
    "SMTP_PASSWORD": {
        "value": "", "value_type": "text", "category": "E-Mail",
        "description": "SMTP-Passwort (verschlüsselt gespeichert)",
        "editable_by_admin": True,
    },
    "SMTP_FROM_EMAIL": {
        "value": "", "value_type": "text", "category": "E-Mail",
        "description": "Absender-E-Mail-Adresse",
        "editable_by_admin": True,
    },
    "SMTP_FROM_NAME": {
        "value": "Verein Tischlein Deck Dich Vorarlberg", "value_type": "text",
        "category": "E-Mail",
        "description": "Angezeigter Absendername",
        "editable_by_admin": True,
    },
    "SMTP_USE_TLS": {
        "value": True, "value_type": "bool", "category": "E-Mail",
        "description": "STARTTLS verwenden (empfohlen für Port 587)",
        "editable_by_admin": True,
    },
    # ── Anspruchsgrenzen ──────────────────────────────────────────────────────
    "BASE_LIMIT": {
        "value": 820.0,
        "value_type": "number",
        "category": "Anspruchsgrenzen",
        "description": "Basisgrenze pro erwachsene Person.",
        "editable_by_admin": True,
    },
    "ADDITIONAL_ADULT_LIMIT": {
        "value": 390.0,
        "value_type": "number",
        "category": "Anspruchsgrenzen",
        "description": "Zuschlag für weitere erwachsene Haushaltsmitglieder.",
        "editable_by_admin": True,
    },
    "CHILD_LIMIT": {
        "value": 185.0,
        "value_type": "number",
        "category": "Anspruchsgrenzen",
        "description": "Zuschlag für Kinder.",
        "editable_by_admin": True,
    },
    "HARDSHIP_FACTOR": {
        "value": 1.1,
        "value_type": "number",
        "category": "Härtefall",
        "description": "Multiplikator zur Berechnung der Härtefallgrenze.",
        "editable_by_admin": True,
    },
}


class SettingsService:
    def __init__(self, repository: SettingRepository | None = None):
        initialize_database()
        self.repository = repository or SettingRepository()
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        for key, definition in DEFAULT_SETTINGS.items():
            self.repository.create_setting(
                key=key,
                value=definition["value"],
                value_type=definition["value_type"],
                category=definition.get("category"),
                description=definition.get("description"),
                editable_by_admin=definition.get("editable_by_admin", True),
            )

    def get(self, key: str, default: Any = None) -> Any:
        setting = self.repository.get_setting(key)
        if setting is None:
            return default
        return setting["value"]

    def get_setting(self, key: str) -> dict[str, Any] | None:
        return self.repository.get_setting(key)

    def get_all_settings(self) -> list[dict[str, Any]]:
        return self.repository.get_all_settings()

    def get_all(self) -> dict[str, Any]:
        return {setting["key"]: setting["value"] for setting in self.get_all_settings()}

    def update_setting(self, key: str, value: Any, comment: str | None = None) -> dict[str, Any]:
        if not Session.is_admin():
            raise PermissionError("Nur Admin-Benutzer dürfen Prüfparameter ändern.")

        setting = self.repository.get_setting(key)
        if setting is None:
            raise KeyError(f"Einstellung '{key}' nicht gefunden.")

        old_value = setting["value"]
        self.repository.update_setting_value(key, value, updated_by=Session.get_user_id())
        self._record_audit_log(setting["id"], key, old_value, value, comment)
        return self.repository.get_setting(key)

    def _record_audit_log(
        self,
        setting_id: int,
        key: str,
        old_value: Any,
        new_value: Any,
        comment: str | None,
    ) -> None:
        details = {
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
            "comment": comment,
        }
        payload = json.dumps(details, ensure_ascii=False)
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO audit_logs (user_id, action, object_type, object_id, details) VALUES (?, ?, ?, ?, ?)",
                (
                    Session.get_user_id(),
                    "update_setting",
                    "setting",
                    setting_id,
                    payload,
                ),
            )
            connection.commit()
