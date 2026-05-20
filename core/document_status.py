from __future__ import annotations

from typing import ClassVar, Dict, List


class DocumentStatus:
    VORHANDEN: ClassVar[str] = "VORHANDEN"
    GEPRUEFT: ClassVar[str] = "GEPRUEFT"
    FEHLT: ClassVar[str] = "FEHLT"
    ARCHIVIERT: ClassVar[str] = "ARCHIVIERT"
    UNGUELTIG: ClassVar[str] = "UNGUELTIG"

    ALL_STATUSES: ClassVar[List[str]] = [
        VORHANDEN,
        GEPRUEFT,
        FEHLT,
        ARCHIVIERT,
        UNGUELTIG,
    ]

    DISPLAY_NAMES: ClassVar[Dict[str, str]] = {
        VORHANDEN: "Vorhanden",
        GEPRUEFT: "Geprüft",
        FEHLT: "Fehlt",
        ARCHIVIERT: "Archiviert",
        UNGUELTIG: "Ungültig",
    }

    @classmethod
    def get_display(cls, status: str) -> str:
        return cls.DISPLAY_NAMES.get(status, status)
