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

    # ── Supervisor-Benachrichtigungen (Anforderung 10) ────────────────────────

    def notify_supervisors_new_case(
        self,
        case_number: str,
        claim_id: int,
        location_id: int | None = None,
        with_documents: bool = False,
    ) -> None:
        """
        Benachrichtigt alle Supervisor/Standortleitung dass ein neuer Fall
        angelegt wurde und Unterlagen zur Prüfung vorliegen.
        Supervisors erhalten die Meldung im Cockpit/Dashboard.
        """
        msg = f"Neuer Fall {case_number} angelegt"
        if with_documents:
            msg += " – Dokumente hochgeladen, Unterlagen prüfen und Anspruchsberechtigung beurteilen."
        else:
            msg += " – Unterlagen und Anspruchsberechtigung prüfen."

        # Broadcast: user_id=None → alle Supervisors sehen die Meldung
        # (Alternativ: gezielt pro Standort filtern wenn user-Tabelle erweitert wird)
        self.notify(
            title=f"Neuer Fall zur Prüfung: {case_number}",
            message=msg,
            type_="CLAIM",
            user_id=None,
            reference_type="claim",
            reference_id=claim_id,
        )

    def notify_supervisors_approval_required(
        self,
        case_number: str,
        claim_id: int,
        reason: str,
    ) -> None:
        """Benachrichtigt Supervisors dass ein Fall Freigabe erfordert (4-Augen)."""
        self.notify(
            title=f"Freigabe erforderlich: {case_number}",
            message=f"Fall {case_number} erfordert Vier-Augen-Freigabe. Grund: {reason}",
            type_="CLAIM",
            user_id=None,
            reference_type="claim",
            reference_id=claim_id,
        )

    def notify_supervisors_first_evaluation_done(
        self,
        case_number: str,
        claim_id: int,
        examiner_name: str,
        status_display: str,
        evaluation_date: str,
    ) -> None:
        """Benachrichtigt Supervisors nach abgeschlossener Erstprüfung durch Mitarbeiter."""
        self.notify(
            title=f"Erstprüfung abgeschlossen: {case_number}",
            message=(
                f"Mitarbeiter: {examiner_name} | "
                f"Status: {status_display} | "
                f"Datum: {evaluation_date[:10] if evaluation_date else '-'} | "
                "Überprüfung oder Freigabe zur erneuten Prüfung ggf. erforderlich."
            ),
            type_="CLAIM",
            user_id=None,
            reference_type="claim",
            reference_id=claim_id,
        )

    def notify_re_evaluation_requested(
        self,
        case_number: str,
        claim_id: int,
        requester_name: str,
        reason: str | None,
    ) -> None:
        """Benachrichtigt Supervisors, dass ein Mitarbeiter erneute Prüfung beantragt hat."""
        self.notify(
            title=f"Freigabe erneute Prüfung: {case_number}",
            message=(
                f"Angefordert von: {requester_name} | "
                f"Grund: {reason or '(kein Grund angegeben)'}"
            ),
            type_="CLAIM",
            user_id=None,
            reference_type="claim",
            reference_id=claim_id,
        )

    def notify_age_alert(self, message: str, claim_id: int) -> None:
        """Dashboard-Meldung für 20-Jahre-Altersgrenze."""
        self.notify(
            title="Altersgrenze-Prüfung erforderlich",
            message=message,
            type_="CLAIM",
            user_id=None,
            reference_type="claim",
            reference_id=claim_id,
        )
