from core.session import Session
from database.repositories.appointment_repository import AppointmentRepository


APPOINTMENT_STATUSES = ["GEPLANT", "BESTÄTIGT", "ABGESCHLOSSEN", "ABGESAGT"]


class AppointmentService:
    def __init__(self, repo: AppointmentRepository | None = None):
        self.repo = repo or AppointmentRepository()

    def create_appointment(self, data: dict) -> int:
        if not data.get("title", "").strip():
            raise ValueError("Titel darf nicht leer sein.")
        if not data.get("appointment_date", "").strip():
            raise ValueError("Datum ist Pflichtfeld.")
        data.setdefault("created_by", Session.get_user_id())
        return self.repo.create(data)

    def list_appointments(self, status: str | None = None,
                          user_id: int | None = None,
                          location_id: int | None = None,
                          from_date: str | None = None,
                          to_date: str | None = None) -> list[dict]:
        return self.repo.list_all(
            status=status,
            user_id=user_id,
            location_id=location_id,
            from_date=from_date,
            to_date=to_date,
        )

    def get_appointment(self, appointment_id: int) -> dict | None:
        return self.repo.get_by_id(appointment_id)

    def update_appointment(self, appointment_id: int, data: dict) -> None:
        if not data.get("title", "").strip():
            raise ValueError("Titel darf nicht leer sein.")
        self.repo.update(appointment_id, data)

    def delete_appointment(self, appointment_id: int) -> None:
        self.repo.delete(appointment_id)

    def list_for_person(self, person_id: int) -> list[dict]:
        return self.repo.list_for_person(person_id)

    def get_upcoming(self, days: int = 7) -> list[dict]:
        return self.repo.list_upcoming(days)

    def count_today(self) -> int:
        return self.repo.count_today()
