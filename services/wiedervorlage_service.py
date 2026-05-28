"""Wiedervorlage-/Aufgabenerinnerungs-Service."""
from core.session import Session
from database.repositories.wiedervorlage_repository import WiedervorlageRepository


class WiedervorlageService:

    def __init__(self, repo: WiedervorlageRepository | None = None):
        self.repo = repo or WiedervorlageRepository()

    def create(
        self,
        due_date: str,
        note: str | None = None,
        claim_id: int | None = None,
        person_id: int | None = None,
    ) -> int:
        user_id = Session.get_user_id()
        if not user_id:
            raise ValueError("Kein Benutzer angemeldet.")
        if not due_date:
            raise ValueError("Wiedervorlagedatum ist Pflichtfeld.")
        return self.repo.create(user_id, due_date, note, claim_id, person_id)

    def list_open(self) -> list[dict]:
        user_id = Session.get_user_id()
        if not user_id:
            return []
        return self.repo.list_for_user(user_id, only_open=True)

    def list_due_today(self) -> list[dict]:
        user_id = Session.get_user_id()
        if not user_id:
            return []
        return self.repo.list_due_today(user_id)

    def count_due(self) -> int:
        user_id = Session.get_user_id()
        if not user_id:
            return 0
        return self.repo.count_due(user_id)

    def mark_done(self, wiedervorlage_id: int) -> None:
        self.repo.mark_done(wiedervorlage_id)

    def delete(self, wiedervorlage_id: int) -> None:
        self.repo.delete(wiedervorlage_id)
