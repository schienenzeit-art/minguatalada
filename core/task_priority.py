from __future__ import annotations

from typing import ClassVar, Dict, List


class TaskPriority:
    KRITISCH: ClassVar[str] = "KRITISCH"
    HOCH: ClassVar[str] = "HOCH"
    MITTEL: ClassVar[str] = "MITTEL"
    NIEDRIG: ClassVar[str] = "NIEDRIG"
    NORMAL: ClassVar[str] = MITTEL

    ALL_PRIORITIES: ClassVar[List[str]] = [
        KRITISCH,
        HOCH,
        MITTEL,
        NIEDRIG,
    ]

    DISPLAY_NAMES: ClassVar[Dict[str, str]] = {
        KRITISCH: "Kritisch",
        HOCH: "Hoch",
        MITTEL: "Normal",
        NIEDRIG: "Niedrig",
    }

    @classmethod
    def get_display(cls, priority: str) -> str:
        return cls.DISPLAY_NAMES.get(priority, priority)
