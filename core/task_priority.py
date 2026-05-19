from __future__ import annotations

from typing import ClassVar, Dict, List


class TaskPriority:
    HOCH: ClassVar[str] = "HOCH"
    MITTEL: ClassVar[str] = "MITTEL"
    NIEDRIG: ClassVar[str] = "NIEDRIG"

    ALL_PRIORITIES: ClassVar[List[str]] = [
        HOCH,
        MITTEL,
        NIEDRIG,
    ]

    DISPLAY_NAMES: ClassVar[Dict[str, str]] = {
        HOCH: "Hoch",
        MITTEL: "Mittel",
        NIEDRIG: "Niedrig",
    }

    @classmethod
    def get_display(cls, priority: str) -> str:
        return cls.DISPLAY_NAMES.get(priority, priority)
