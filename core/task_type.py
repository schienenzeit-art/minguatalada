from __future__ import annotations

from typing import ClassVar, Dict, List


class TaskType:
    ALLGEMEIN: ClassVar[str] = "Allgemein"
    PRUEFUNG: ClassVar[str] = "Prüfung"
    DOKUMENT: ClassVar[str] = "Dokument"
    KARTE: ClassVar[str] = "Karte"
    WIEDERVORLAGE: ClassVar[str] = "Wiedervorlage"

    ALL_TYPES: ClassVar[List[str]] = [
        ALLGEMEIN,
        PRUEFUNG,
        DOKUMENT,
        KARTE,
        WIEDERVORLAGE,
    ]

    DISPLAY_NAMES: ClassVar[Dict[str, str]] = {
        ALLGEMEIN: "Allgemein",
        PRUEFUNG: "Prüfung",
        DOKUMENT: "Dokument",
        KARTE: "Karte",
        WIEDERVORLAGE: "Wiedervorlage",
    }

    @classmethod
    def get_display(cls, task_type: str) -> str:
        return cls.DISPLAY_NAMES.get(task_type, task_type)
