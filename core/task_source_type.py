from __future__ import annotations

from typing import ClassVar, Dict, List


class TaskSourceType:
    MANUAL: ClassVar[str] = "manual"
    SYSTEM: ClassVar[str] = "system"

    ALL_TYPES: ClassVar[List[str]] = [MANUAL, SYSTEM]

    DISPLAY_NAMES: ClassVar[Dict[str, str]] = {
        MANUAL: "Manuell",
        SYSTEM: "System",
    }

    @classmethod
    def get_display(cls, source_type: str) -> str:
        return cls.DISPLAY_NAMES.get(source_type, source_type)
