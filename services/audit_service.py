from core.session import Session
from database.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, repo: AuditRepository | None = None):
        self.repo = repo or AuditRepository()

    def log(self, action: str, object_type: str,
            object_id: int | None = None, details: str | None = None) -> None:
        user_id = Session.get_user_id()
        self.repo.log(user_id, action, object_type, object_id, details)

    def list_logs(self, object_type: str | None = None,
                  user_id: int | None = None,
                  limit: int = 200, offset: int = 0) -> list[dict]:
        return self.repo.list_logs(
            object_type=object_type,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    def count(self, object_type: str | None = None, user_id: int | None = None) -> int:
        return self.repo.count(object_type=object_type, user_id=user_id)

    def cleanup(self, days: int = 2555) -> int:
        return self.repo.delete_old(days)
