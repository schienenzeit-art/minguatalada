from datetime import date, timedelta
from typing import List, Dict, Optional

from core.card_status import CardStatus
from core.claim_status import ClaimStatus
from core.task_status import TaskStatus
from services.card_service import CardService
from services.claim_service import ClaimService
from services.location_service import LocationService
from services.task_service import TaskService


class DashboardService:
    def __init__(
        self,
        claim_service: ClaimService | None = None,
        card_service: CardService | None = None,
        location_service: LocationService | None = None,
        task_service: TaskService | None = None,
    ):
        self.claim_service = claim_service or ClaimService()
        self.card_service = card_service or CardService()
        self.location_service = location_service or LocationService()
        self.task_service = task_service or TaskService()

    def get_kpi_items(self) -> List[Dict[str, object]]:
        today = date.today().isoformat()
        return [
            {
                "title": "Offene Aufgaben",
                "value": str(self.task_service.count_open_tasks()),
                "subtitle": "Manuelle und systemgenerierte Aufgaben",
                "page": "tasks",
                "filters": {"status": TaskStatus.OFFEN},
                "accent": "#d1495b",
            },
            {
                "title": "Offene Ansprüche",
                "value": str(self.claim_service.count_claims(status=ClaimStatus.IN_PRUEFUNG)),
                "subtitle": "Fälle mit laufender Prüfung",
                "page": "claims",
                "filters": {"status": ClaimStatus.IN_PRUEFUNG},
                "accent": "#e74c3c",
            },
            {
                "title": "Laufende Karten",
                "value": str(
                    self.card_service.count_cards(statuses=[CardStatus.AKTIV, CardStatus.BALD_ABLAUFEND])
                ),
                "subtitle": "Aktive und bald ablaufende Karten",
                "page": "cards",
                "filters": {"status": CardStatus.AKTIV},
                "accent": "#0f9d58",
            },
            {
                "title": "Genehmigte Fälle",
                "value": str(
                    self.claim_service.count_claims(
                        statuses=[ClaimStatus.ANSPRUCHSBERECHTIGT, ClaimStatus.HAERTEFALL]
                    )
                ),
                "subtitle": "Fälle mit positivem Bescheid",
                "page": "claims",
                "filters": {"statuses": [ClaimStatus.ANSPRUCHSBERECHTIGT, ClaimStatus.HAERTEFALL]},
                "accent": "#2383e2",
            },
            {
                "title": "Abgelehnte Fälle",
                "value": str(self.claim_service.count_claims(status=ClaimStatus.ABGELEHNT)),
                "subtitle": "Fälle mit Ablehnung",
                "page": "claims",
                "filters": {"status": ClaimStatus.ABGELEHNT},
                "accent": "#f39c12",
            },
        ]

    def get_recent_claims(self, status: str | None = None, limit: int = 5) -> list[dict]:
        # If no status specified, default to IN_PRUEFUNG (open cases)
        if status is None:
            status = ClaimStatus.IN_PRUEFUNG
        claims = self.claim_service.list_claims(status=status)
        return claims[:limit]

    def get_summary_items(self) -> List[Dict[str, object]]:
        return [
            {
                "title": "Heutige Prüfungen",
                "value": str(self.claim_service.count_claims(start_date=date.today().isoformat())),
                "subtitle": "Fälle mit Prüfstart heute",
                "accent": "#7f8c8d",
            },
            {
                "title": "Karten in 30 Tagen ablaufend",
                "value": str(self.card_service.count_expiring_cards(days=30)),
                "subtitle": "Karten, die bald erneuert werden müssen",
                "accent": "#e67e22",
            },
            {
                "title": "Neue Anträge (7 Tage)",
                "value": str(self.claim_service.count_claims(created_since_days=7)),
                "subtitle": "Neu eingegangene Fälle der letzten Woche",
                "accent": "#8e44ad",
            },
            {
                "title": "Aktive Standorte",
                "value": str(len(self.location_service.list_active_locations())),
                "subtitle": "Standorte mit aktivem Betrieb",
                "accent": "#16a085",
            },
        ]

    def refresh(self) -> None:
        # Reserviert für späteren Cache-Mechanismus
        pass
