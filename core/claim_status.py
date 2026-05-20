from __future__ import annotations

from typing import ClassVar, Dict, List


class ClaimStatus:
    IN_PRUEFUNG: ClassVar[str] = "IN_PRUEFUNG"
    ANSPRUCHSBERECHTIGT: ClassVar[str] = "ANSPRUCHSBERECHTIGT"
    HAERTEFALL: ClassVar[str] = "HAERTEFALL"
    ABGELEHNT: ClassVar[str] = "ABGELEHNT"
    ABGELAUFEN: ClassVar[str] = "ABGELAUFEN"
    ARCHIVIERT: ClassVar[str] = "ARCHIVIERT"

    ALL_STATUSES: ClassVar[List[str]] = [
        IN_PRUEFUNG,
        ANSPRUCHSBERECHTIGT,
        HAERTEFALL,
        ABGELEHNT,
        ABGELAUFEN,
        ARCHIVIERT,
    ]

    DISPLAY_NAMES: ClassVar[Dict[str, str]] = {
        IN_PRUEFUNG: "In Prüfung",
        ANSPRUCHSBERECHTIGT: "anspruchsberechtigt",
        HAERTEFALL: "Härtefall",
        ABGELEHNT: "abgelehnt",
        ABGELAUFEN: "abgelaufen",
        ARCHIVIERT: "archiviert",
    }

    ROLE_TRANSITIONS: ClassVar[Dict[str, Dict[str, List[str]]]] = {
        "Mitarbeiter": {
            IN_PRUEFUNG: [ANSPRUCHSBERECHTIGT, HAERTEFALL, ABGELEHNT],
        },
        "Standortleitung": {
            IN_PRUEFUNG: [ANSPRUCHSBERECHTIGT, HAERTEFALL, ABGELEHNT],
            ANSPRUCHSBERECHTIGT: [ABGELAUFEN, ARCHIVIERT],
            HAERTEFALL: [ABGELAUFEN, ARCHIVIERT],
            ABGELEHNT: [ARCHIVIERT],
        },
        "Admin": {
            IN_PRUEFUNG: [ANSPRUCHSBERECHTIGT, HAERTEFALL, ABGELEHNT, ABGELAUFEN, ARCHIVIERT],
            ANSPRUCHSBERECHTIGT: [IN_PRUEFUNG, HAERTEFALL, ABGELEHNT, ABGELAUFEN, ARCHIVIERT],
            HAERTEFALL: [IN_PRUEFUNG, ANSPRUCHSBERECHTIGT, ABGELEHNT, ABGELAUFEN, ARCHIVIERT],
            ABGELEHNT: [IN_PRUEFUNG, ANSPRUCHSBERECHTIGT, HAERTEFALL, ABGELAUFEN, ARCHIVIERT],
            ABGELAUFEN: [IN_PRUEFUNG, ANSPRUCHSBERECHTIGT, HAERTEFALL, ARCHIVIERT],
            ARCHIVIERT: [IN_PRUEFUNG, ANSPRUCHSBERECHTIGT, HAERTEFALL, ABGELEHNT],
        },
    }

    @classmethod
    def is_valid_status(cls, status: str) -> bool:
        return status in cls.ALL_STATUSES

    @classmethod
    def get_display(cls, status: str) -> str:
        return cls.DISPLAY_NAMES.get(status, status)

    @classmethod
    def get_allowed_transitions(cls, current_status: str, role_name: str) -> List[str]:
        if role_name not in cls.ROLE_TRANSITIONS:
            return []
        return cls.ROLE_TRANSITIONS[role_name].get(current_status, [])

    @classmethod
    def can_transition(cls, current_status: str, target_status: str, role_name: str) -> bool:
        return target_status in cls.get_allowed_transitions(current_status, role_name)
