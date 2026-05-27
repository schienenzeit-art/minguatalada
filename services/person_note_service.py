from core.session import Session
from database.repositories.person_note_repository import PersonNoteRepository


class PersonNoteService:
    def __init__(self, repo: PersonNoteRepository | None = None):
        self.repo = repo or PersonNoteRepository()

    def list_notes(self, person_id: int) -> list[dict]:
        return self.repo.list_for_person(person_id)

    def add_note(self, person_id: int, note_text: str) -> int:
        note_text = note_text.strip()
        if not note_text:
            raise ValueError("Notiz darf nicht leer sein.")
        user_id = Session.get_user_id()
        return self.repo.create(person_id, user_id, note_text)

    def delete_note(self, note_id: int) -> None:
        self.repo.delete(note_id)

    def update_note(self, note_id: int, note_text: str) -> None:
        note_text = note_text.strip()
        if not note_text:
            raise ValueError("Notiz darf nicht leer sein.")
        self.repo.update(note_id, note_text)
