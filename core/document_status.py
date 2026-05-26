from __future__ import annotations

from typing import ClassVar, Dict, List


class DocumentStatus:
    EINGEGANGEN: ClassVar[str] = "EINGEGANGEN"
    VORHANDEN: ClassVar[str] = "VORHANDEN"
    GEPRUEFT: ClassVar[str] = "GEPRUEFT"
    UNVOLLSTAENDIG: ClassVar[str] = "UNVOLLSTAENDIG"
    FEHLT: ClassVar[str] = "FEHLT"
    ARCHIVIERT: ClassVar[str] = "ARCHIVIERT"
    UNGUELTIG: ClassVar[str] = "UNGUELTIG"

    ALL_STATUSES: ClassVar[List[str]] = [
        EINGEGANGEN,
        VORHANDEN,
        GEPRUEFT,
        UNVOLLSTAENDIG,
        FEHLT,
        ARCHIVIERT,
        UNGUELTIG,
    ]

    DISPLAY_NAMES: ClassVar[Dict[str, str]] = {
        EINGEGANGEN: "Eingegangen",
        VORHANDEN: "Vorhanden",
        GEPRUEFT: "Geprüft",
        UNVOLLSTAENDIG: "Unvollständig",
        FEHLT: "Fehlt",
        ARCHIVIERT: "Archiviert",
        UNGUELTIG: "Ungültig",
    }

    @classmethod
    def get_display(cls, status: str) -> str:
        return cls.DISPLAY_NAMES.get(status, status)
