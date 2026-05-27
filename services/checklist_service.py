from core.session import Session
from database.repositories.checklist_repository import ChecklistRepository


class ChecklistService:
    def __init__(self, repo: ChecklistRepository | None = None):
        self.repo = repo or ChecklistRepository()

    # ── Templates ─────────────────────────────────────────────────────────────
    def list_templates(self) -> list[dict]:
        return self.repo.list_templates()

    def create_template(self, name: str, category_id: int | None = None) -> int:
        if not name.strip():
            raise ValueError("Vorlagenname darf nicht leer sein.")
        return self.repo.create_template(name.strip(), category_id)

    def delete_template(self, template_id: int) -> None:
        self.repo.delete_template(template_id)

    def list_template_items(self, template_id: int) -> list[dict]:
        return self.repo.list_items_for_template(template_id)

    def add_template_item(self, template_id: int, label: str,
                          is_required: bool = True, sort_order: int = 0) -> int:
        if not label.strip():
            raise ValueError("Bezeichnung darf nicht leer sein.")
        return self.repo.add_template_item(template_id, label.strip(), is_required, sort_order)

    def delete_template_item(self, item_id: int) -> None:
        self.repo.delete_template_item(item_id)

    # ── Claim-Checklisten ──────────────────────────────────────────────────────
    def list_claim_items(self, claim_id: int) -> list[dict]:
        return self.repo.list_claim_items(claim_id)

    def add_claim_item(self, claim_id: int, label: str,
                       is_required: bool = False) -> int:
        if not label.strip():
            raise ValueError("Bezeichnung darf nicht leer sein.")
        existing = self.repo.list_claim_items(claim_id)
        sort_order = len(existing)
        return self.repo.add_claim_item(claim_id, label.strip(), is_required, sort_order)

    def set_item_checked(self, item_id: int, checked: bool) -> None:
        user_id = Session.get_user_id()
        self.repo.set_item_checked(item_id, checked, user_id)

    def delete_claim_item(self, item_id: int) -> None:
        self.repo.delete_claim_item(item_id)

    def apply_template(self, claim_id: int, template_id: int) -> int:
        return self.repo.apply_template_to_claim(claim_id, template_id)

    def completion_rate(self, claim_id: int) -> tuple[int, int]:
        items = self.repo.list_claim_items(claim_id)
        total   = len(items)
        checked = sum(1 for i in items if i.get("is_checked"))
        return checked, total
