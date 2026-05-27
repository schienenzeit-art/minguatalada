from core.session import Session
from database.repositories.approval_repository import ApprovalRepository


class ApprovalService:
    def __init__(self, repo: ApprovalRepository | None = None):
        self.repo = repo or ApprovalRepository()

    def request_approval(self, claim_id: int) -> int:
        user_id = Session.get_user_id()
        return self.repo.create(claim_id, user_id)

    def list_pending(self) -> list[dict]:
        return self.repo.list_pending()

    def list_for_claim(self, claim_id: int) -> list[dict]:
        return self.repo.list_for_claim(claim_id)

    def approve(self, request_id: int, comment: str | None = None) -> None:
        user_id = Session.get_user_id()
        if not user_id:
            raise PermissionError("Kein angemeldeter Benutzer.")
        self.repo.review(request_id, user_id, "APPROVED", comment)

    def reject(self, request_id: int, comment: str | None = None) -> None:
        user_id = Session.get_user_id()
        if not user_id:
            raise PermissionError("Kein angemeldeter Benutzer.")
        if not comment:
            raise ValueError("Ablehnungsgrund ist Pflichtfeld.")
        self.repo.review(request_id, user_id, "REJECTED", comment)

    def count_pending(self) -> int:
        return self.repo.count_pending()
