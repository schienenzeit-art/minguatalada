"""Applikationsweiter Kontext für den aktuell geöffneten Fall.

Wird von Seiten gesetzt wenn ein Fall geöffnet wird.
TopBar und andere UI-Komponenten können es abfragen um kontextbezogene
Aktionen (Drucken, Mailen, Karte, Wiedervorlage) anzubieten.
"""
from typing import Any


class CaseContext:
    """Singleton-ähnlicher Klassenkontext — kein Threading-Overhead nötig."""

    _claim_id: int | None = None
    _claim: dict[str, Any] | None = None
    _person_id: int | None = None

    @classmethod
    def set(cls, claim_id: int | None, claim: dict | None = None) -> None:
        cls._claim_id  = claim_id
        cls._claim     = claim
        cls._person_id = (claim or {}).get("person_id") if claim else None

    @classmethod
    def clear(cls) -> None:
        cls._claim_id  = None
        cls._claim     = None
        cls._person_id = None

    @classmethod
    def get_claim_id(cls) -> int | None:
        return cls._claim_id

    @classmethod
    def get_claim(cls) -> dict | None:
        return cls._claim

    @classmethod
    def get_person_id(cls) -> int | None:
        return cls._person_id

    @classmethod
    def is_active(cls) -> bool:
        return cls._claim_id is not None

    @classmethod
    def get_case_number(cls) -> str:
        return (cls._claim or {}).get("case_number", "") if cls._claim else ""

    @classmethod
    def get_status(cls) -> str:
        return (cls._claim or {}).get("status", "") if cls._claim else ""

    @classmethod
    def get_person_email(cls) -> str:
        return (cls._claim or {}).get("person_email", "") if cls._claim else ""
