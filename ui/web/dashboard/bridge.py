from PyQt6.QtCore import QObject, pyqtSlot
from core.claim_status import ClaimStatus
from services.dashboard_service import DashboardService


class DashboardWebBridge(QObject):
    def __init__(self, dashboard_service: DashboardService, navigate_callback=None):
        super().__init__()
        self.dashboard_service = dashboard_service
        self.navigate_callback = navigate_callback

    @pyqtSlot(result=list)
    def get_kpi_items(self) -> list:
        items = self.dashboard_service.get_kpi_items()
        for item in items:
            if item.get("filters") and item["filters"].get("status"):
                item["filters"]["status_display"] = ClaimStatus.get_display(
                    item["filters"]["status"]
                )
        return items

    @pyqtSlot(str, int, result=list)
    def get_recent_claims(self, status: str, limit: int) -> list:
        if status == "":
            status = None
        claims = self.dashboard_service.get_recent_claims(status=status, limit=limit)
        return [self._serialize_claim(claim) for claim in claims]

    @pyqtSlot(str, 'QVariant')
    def navigate(self, page: str, filters) -> None:
        if self.navigate_callback:
            self.navigate_callback(page, dict(filters) if filters else None)

    @pyqtSlot(str, result=str)
    def get_status_label(self, status: str) -> str:
        return ClaimStatus.get_display(status)

    def _serialize_claim(self, claim: dict) -> dict:
        return {
            "id": claim.get("id"),
            "case_number": claim.get("case_number") or "-",
            "person_display_name": claim.get("person_display_name") or claim.get("user_name") or "-",
            "status": claim.get("status") or "-",
            "location_name": claim.get("location_name") or "-",
            "created_at": claim.get("created_at") and claim.get("created_at")[:10] or "-",
        }
