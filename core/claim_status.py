from __future__ import annotations

from typing import ClassVar, Dict, List


class ClaimStatus:
    IN_PRUEFUNG: ClassVar[str] = "IN_PRUEFUNG"
    ANSPRUCHSBERECHTIGT: ClassVar[str] = "ANSPRUCHSBERECHTIGT"
    HAERTEFALL: ClassVar[str] = "HAERTEFALL"
    ABGELEHNT: ClassVar[str] = "ABGELEHNT"
    VORLAEFIG_ABGELEHNT: ClassVar[str] = "VORLAEFIG_ABGELEHNT"
    FREIGABE_KARTE: ClassVar[str] = "FREIGABE_KARTE"
    ABGELAUFEN: ClassVar[str] = "ABGELAUFEN"
    ARCHIVIERT: ClassVar[str] = "ARCHIVIERT"
    WIDERSPRUCH: ClassVar[str] = "WIDERSPRUCH"

    ALL_STATUSES: ClassVar[List[str]] = [
        IN_PRUEFUNG,
        ANSPRUCHSBERECHTIGT,
        HAERTEFALL,
        VORLAEFIG_ABGELEHNT,
        FREIGABE_KARTE,
        ABGELEHNT,
        ABGELAUFEN,
        ARCHIVIERT,
        WIDERSPRUCH,
    ]

    DISPLAY_NAMES: ClassVar[Dict[str, str]] = {
        IN_PRUEFUNG: "In Prüfung",
        ANSPRUCHSBERECHTIGT: "Anspruchsberechtigt",
        HAERTEFALL: "Härtefall",
        VORLAEFIG_ABGELEHNT: "Vorläufig Abgelehnt",
        FREIGABE_KARTE: "Freigabe Karte",
        ABGELEHNT: "Abgelehnt",
        ABGELAUFEN: "Abgelaufen",
        ARCHIVIERT: "Archiviert",
        WIDERSPRUCH: "Widerspruch",
    }

    # Statuses die ein 4-Augen-Freigabeverfahren erfordern
    REQUIRES_APPROVAL: ClassVar[List[str]] = [
        HAERTEFALL,
        VORLAEFIG_ABGELEHNT,
        FREIGABE_KARTE,
    ]

    ROLE_TRANSITIONS: ClassVar[Dict[str, Dict[str, List[str]]]] = {
        "Mitarbeiter": {
            IN_PRUEFUNG: [ANSPRUCHSBERECHTIGT, HAERTEFALL, ABGELEHNT, VORLAEFIG_ABGELEHNT],
            ANSPRUCHSBERECHTIGT: [FREIGABE_KARTE],
            ABGELEHNT: [WIDERSPRUCH],
            VORLAEFIG_ABGELEHNT: [WIDERSPRUCH],
        },
        "Standortleitung": {
            IN_PRUEFUNG: [ANSPRUCHSBERECHTIGT, HAERTEFALL, ABGELEHNT, VORLAEFIG_ABGELEHNT],
            ANSPRUCHSBERECHTIGT: [FREIGABE_KARTE, ABGELAUFEN, ARCHIVIERT],
            HAERTEFALL: [ABGELAUFEN, ARCHIVIERT, ANSPRUCHSBERECHTIGT],
            FREIGABE_KARTE: [ANSPRUCHSBERECHTIGT, ABGELEHNT, IN_PRUEFUNG],
            VORLAEFIG_ABGELEHNT: [IN_PRUEFUNG, ABGELEHNT, ARCHIVIERT],
            ABGELEHNT: [ARCHIVIERT, WIDERSPRUCH],
            WIDERSPRUCH: [IN_PRUEFUNG, ABGELEHNT, ARCHIVIERT],
        },
        "Supervisor": {
            IN_PRUEFUNG: [ANSPRUCHSBERECHTIGT, HAERTEFALL, ABGELEHNT, VORLAEFIG_ABGELEHNT],
            ANSPRUCHSBERECHTIGT: [FREIGABE_KARTE, ABGELAUFEN, ARCHIVIERT],
            HAERTEFALL: [ABGELAUFEN, ARCHIVIERT, ANSPRUCHSBERECHTIGT],
            FREIGABE_KARTE: [ANSPRUCHSBERECHTIGT, ABGELEHNT, IN_PRUEFUNG],
            VORLAEFIG_ABGELEHNT: [IN_PRUEFUNG, ABGELEHNT, ARCHIVIERT],
            ABGELEHNT: [ARCHIVIERT, WIDERSPRUCH],
            WIDERSPRUCH: [IN_PRUEFUNG, ABGELEHNT, ARCHIVIERT],
        },
        "Admin": {
            IN_PRUEFUNG: [ANSPRUCHSBERECHTIGT, HAERTEFALL, ABGELEHNT, VORLAEFIG_ABGELEHNT, FREIGABE_KARTE, ABGELAUFEN, ARCHIVIERT, WIDERSPRUCH],
            ANSPRUCHSBERECHTIGT: [IN_PRUEFUNG, HAERTEFALL, ABGELEHNT, VORLAEFIG_ABGELEHNT, FREIGABE_KARTE, ABGELAUFEN, ARCHIVIERT, WIDERSPRUCH],
            HAERTEFALL: [IN_PRUEFUNG, ANSPRUCHSBERECHTIGT, ABGELEHNT, VORLAEFIG_ABGELEHNT, FREIGABE_KARTE, ABGELAUFEN, ARCHIVIERT, WIDERSPRUCH],
            VORLAEFIG_ABGELEHNT: [IN_PRUEFUNG, ANSPRUCHSBERECHTIGT, HAERTEFALL, ABGELEHNT, ARCHIVIERT, WIDERSPRUCH],
            FREIGABE_KARTE: [ANSPRUCHSBERECHTIGT, ABGELEHNT, IN_PRUEFUNG, ARCHIVIERT],
            ABGELEHNT: [IN_PRUEFUNG, ANSPRUCHSBERECHTIGT, HAERTEFALL, VORLAEFIG_ABGELEHNT, ABGELAUFEN, ARCHIVIERT, WIDERSPRUCH],
            ABGELAUFEN: [IN_PRUEFUNG, ANSPRUCHSBERECHTIGT, HAERTEFALL, ARCHIVIERT, WIDERSPRUCH],
            ARCHIVIERT: [IN_PRUEFUNG, ANSPRUCHSBERECHTIGT, HAERTEFALL, ABGELEHNT, WIDERSPRUCH],
            WIDERSPRUCH: [IN_PRUEFUNG, ANSPRUCHSBERECHTIGT, HAERTEFALL, ABGELEHNT, ARCHIVIERT],
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
        transitions = cls.ROLE_TRANSITIONS.get(role_name, {})
        return transitions.get(current_status, [])

    @classmethod
    def can_transition(cls, current_status: str, target_status: str, role_name: str) -> bool:
        return target_status in cls.get_allowed_transitions(current_status, role_name)

    @classmethod
    def requires_approval(cls, status: str) -> bool:
        return status in cls.REQUIRES_APPROVAL
