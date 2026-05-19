from __future__ import annotations

from typing import ClassVar, List


class CardStatus:
    """
    Kartenstatus für die Kartenverwaltung.
    
    Statustransitionen:
    - AKTIV: normale, gültige Karte
    - BALD_ABLAUFEND: Ablaufdatum kommt in <30 Tagen
    - ABGELAUFEN: Ablaufdatum vorbei
    - GESPERRT: administrativ gesperrt
    - ARCHIVIERT: archiviert
    """
    
    AKTIV: ClassVar[str] = "AKTIV"
    BALD_ABLAUFEND: ClassVar[str] = "BALD_ABLAUFEND"
    ABGELAUFEN: ClassVar[str] = "ABGELAUFEN"
    GESPERRT: ClassVar[str] = "GESPERRT"
    ARCHIVIERT: ClassVar[str] = "ARCHIVIERT"

    ALL_STATUSES: ClassVar[List[str]] = [
        AKTIV,
        BALD_ABLAUFEND,
        ABGELAUFEN,
        GESPERRT,
        ARCHIVIERT,
    ]

    @classmethod
    def is_valid_status(cls, status: str) -> bool:
        return status in cls.ALL_STATUSES

    @classmethod
    def get_status_display_name(cls, status: str) -> str:
        """Lesbare deutsche Bezeichnung für Status."""
        names = {
            cls.AKTIV: "Aktiv",
            cls.BALD_ABLAUFEND: "Bald ablaufend",
            cls.ABGELAUFEN: "Abgelaufen",
            cls.GESPERRT: "Gesperrt",
            cls.ARCHIVIERT: "Archiviert",
        }
        return names.get(status, status)
