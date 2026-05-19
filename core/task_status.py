from __future__ import annotations

from typing import ClassVar, Dict, List


class TaskStatus:
    OFFEN: ClassVar[str] = "OFFEN"
    IN_BEARBEITUNG: ClassVar[str] = "IN_BEARBEITUNG"
    WARTET: ClassVar[str] = "WARTET"
    ERLEDIGT: ClassVar[str] = "ERLEDIGT"

    ALL_STATUSES: ClassVar[List[str]] = [
        OFFEN,
        IN_BEARBEITUNG,
        WARTET,
        ERLEDIGT,
    ]

    DISPLAY_NAMES: ClassVar[Dict[str, str]] = {
        OFFEN: "Offen",
        IN_BEARBEITUNG: "In Bearbeitung",
        WARTET: "Wartet",
        ERLEDIGT: "Erledigt",
    }

    @classmethod
    def get_display(cls, status: str) -> str:
        return cls.DISPLAY_NAMES.get(status, status)

    @classmethod
    def is_closed(cls, status: str) -> bool:
        return status == cls.ERLEDIGT
