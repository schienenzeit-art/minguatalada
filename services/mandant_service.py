from database.repositories.mandant_repository import MandantRepository


class MandantService:
    def __init__(self, repo: MandantRepository | None = None):
        self.repo = repo or MandantRepository()

    def list_mandants(self, active_only: bool = False) -> list[dict]:
        return self.repo.list_mandants(active_only=active_only)

    def get_by_id(self, mandant_id: int) -> dict | None:
        return self.repo.get_by_id(mandant_id)

    def create_mandant(self, name: str, short_name: str = "", contact_email: str = "",
                       contact_phone: str = "", address: str = "") -> int:
        if not name.strip():
            raise ValueError("Name ist erforderlich.")
        return self.repo.create(
            name=name.strip(), short_name=short_name.strip(),
            contact_email=contact_email.strip(), contact_phone=contact_phone.strip(),
            address=address.strip(),
        )

    def update_mandant(self, mandant_id: int, data: dict) -> None:
        if not data.get("name", "").strip():
            raise ValueError("Name ist erforderlich.")
        self.repo.update(mandant_id, data)

    def set_active(self, mandant_id: int, is_active: bool) -> None:
        self.repo.set_active(mandant_id, is_active)
