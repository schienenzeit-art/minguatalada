from core.session import Session
from database.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, repo: NotificationRepository | None = None):
        self.repo = repo or NotificationRepository()

    # ── Erstellen ─────────────────────────────────────────────────────────────
    def notify(self, title: str, message: str = "", type_: str = "INFO",
               user_id: int | None = None, reference_type: str | None = None,
               reference_id: int | None = None) -> int:
        """Erstellt eine Benachrichtigung für einen Benutzer (oder alle wenn user_id=None)."""
        return self.repo.create(
            user_id=user_id, type_=type_, title=title, message=message,
            reference_type=reference_type, reference_id=reference_id,
        )

    def notify_task_assigned(self, task_title: str, task_id: int, assigned_to: int) -> None:
        self.notify(
            title=f"Aufgabe zugewiesen: {task_title}",
            message="Eine Aufgabe wurde Ihnen zugewiesen.",
            type_="TASK", user_id=assigned_to,
            reference_type="task", reference_id=task_id,
        )

    def notify_claim_status_changed(self, case_number: str, new_status: str,
                                     claim_id: int, user_id: int | None = None) -> None:
        self.notify(
            title=f"Statusänderung: {case_number}",
            message=f"Status geändert zu: {new_status}",
            type_="CLAIM", user_id=user_id,
            reference_type="claim", reference_id=claim_id,
        )

    def notify_card_expiring(self, card_number: str, expiry_date: str,
                              card_id: int, user_id: int | None = None) -> None:
        self.notify(
            title=f"Karte läuft ab: {card_number}",
            message=f"Ablaufdatum: {expiry_date}",
            type_="CARD", user_id=user_id,
            reference_type="card", reference_id=card_id,
        )

    # ── Lesen ─────────────────────────────────────────────────────────────────
    def get_notifications(self, unread_only: bool = False, limit: int = 50) -> list[dict]:
        user_id = Session.get_user_id()
        if user_id is None:
            return []
        return self.repo.list_for_user(user_id, unread_only=unread_only, limit=limit)

    def count_unread(self) -> int:
        user_id = Session.get_user_id()
        if user_id is None:
            return 0
        return self.repo.count_unread(user_id)

    def mark_read(self, notification_id: int) -> None:
        self.repo.mark_read(notification_id)

    def mark_all_read(self) -> None:
        user_id = Session.get_user_id()
        if user_id:
            self.repo.mark_all_read(user_id)

    def cleanup_old(self, days: int = 90) -> int:
        return self.repo.delete_old(days)
