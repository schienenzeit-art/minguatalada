from collections import Counter
from datetime import date
from typing import Optional
import calendar

from core.claim_status import ClaimStatus
from database.repositories.card_repository import CardRepository
from database.repositories.claim_repository import ClaimRepository
from database.repositories.location_repository import LocationRepository
from database.repositories.person_repository import PersonRepository


class ReportService:
    REPORT_LOCATION_NAMES = ["Bludenz", "Feldkirch", "Dornbirn"]
    MONTH_NAME_DE = {
        1: "Jänner",
        2: "Februar",
        3: "März",
        4: "April",
        5: "Mai",
        6: "Juni",
        7: "Juli",
        8: "August",
        9: "September",
        10: "Oktober",
        11: "November",
        12: "Dezember",
    }

    def __init__(
        self,
        location_repository: LocationRepository | None = None,
        claim_repository: ClaimRepository | None = None,
        card_repository: CardRepository | None = None,
        person_repository: PersonRepository | None = None,
    ):
        self.location_repository = location_repository or LocationRepository()
        self.claim_repository = claim_repository or ClaimRepository()
        self.card_repository = card_repository or CardRepository()
        self.person_repository = person_repository or PersonRepository()

    def get_locations(self, include_inactive: bool = False) -> list[dict]:
        return self.location_repository.list_locations(include_inactive=include_inactive)

    def get_fixed_report_locations(self) -> list[dict]:
        active_locations = {loc["name"]: loc for loc in self.get_locations(include_inactive=False)}
        return [active_locations[name] for name in self.REPORT_LOCATION_NAMES if name in active_locations]

    def _get_location_name(self, location_id: Optional[int]) -> str:
        if location_id is None:
            return "Alle Standorte"
        location = next(
            (loc for loc in self.get_locations(include_inactive=True) if loc["id"] == location_id),
            None,
        )
        return location["name"] if location else "Unbekannt"

    def get_period_report(
        self,
        start_date: str,
        end_date: str,
        location_id: Optional[int] = None,
    ) -> dict:
        if location_id is not None and location_id < 0:
            location_id = None

        total_applications = self.claim_repository.count_claims(
            location_id=location_id,
            created_from=start_date,
            created_to=end_date,
        )
        total_evaluations = self.claim_repository.count_claims(
            location_id=location_id,
            evaluation_from=start_date,
            evaluation_to=end_date,
        )
        approved_claims = self.claim_repository.count_claims(
            status=ClaimStatus.ANSPRUCHSBERECHTIGT,
            location_id=location_id,
            evaluation_from=start_date,
            evaluation_to=end_date,
        )
        rejected_claims = self.claim_repository.count_claims(
            status=ClaimStatus.ABGELEHNT,
            location_id=location_id,
            evaluation_from=start_date,
            evaluation_to=end_date,
        )
        hardship_claims = self.claim_repository.count_claims(
            status=ClaimStatus.HAERTEFALL,
            location_id=location_id,
            evaluation_from=start_date,
            evaluation_to=end_date,
        )
        cards_by_location = self.card_repository.count_cards_by_location(
            location_id=location_id,
            issued_from=start_date,
            issued_to=end_date,
        )

        return {
            "location_id": location_id,
            "location_name": self._get_location_name(location_id),
            "start_date": start_date,
            "end_date": end_date,
            "total_applications": total_applications,
            "total_evaluations": total_evaluations,
            "approved_claims": approved_claims,
            "rejected_claims": rejected_claims,
            "hardship_claims": hardship_claims,
            "cards_by_location": cards_by_location,
        }

    def get_location_report(self, location_id: Optional[int] = None) -> dict:
        claims = self.claim_repository.get_claims(location_id=location_id)
        cards = self.card_repository.get_cards(location_id=location_id)

        claim_status_counts = Counter(claim.get("status", "-") for claim in claims)
        card_status_counts = Counter(card.get("status", "-") for card in cards)

        location_name = "Alle Standorte"
        if location_id is not None:
            location = next(
                (loc for loc in self.get_locations(include_inactive=True) if loc["id"] == location_id),
                None,
            )
            location_name = location["name"] if location else location_name

        return {
            "location_id": location_id,
            "location_name": location_name,
            "total_claims": len(claims),
            "total_cards": len(cards),
            "claim_status_counts": [
                {"status": status, "count": count}
                for status, count in claim_status_counts.items()
            ],
            "card_status_counts": [
                {"status": status, "count": count}
                for status, count in card_status_counts.items()
            ],
        }

    def get_customer_monthly_report(self, location_id: Optional[int], year: int, month: int) -> dict:
        report_month = f"{self.MONTH_NAME_DE.get(month, calendar.month_name[month])} {year}"
        last_day = calendar.monthrange(year, month)[1]
        month_start = date(year, month, 1).isoformat()
        month_end = date(year, month, last_day).isoformat()

        new_customers = self.person_repository.count_persons(
            location_id=location_id,
            created_from=month_start,
            created_to=month_end,
        )
        total_customers = self.person_repository.count_persons(
            location_id=location_id,
            created_to=month_end,
        )

        location_name = "Alle Standorte"
        if location_id is not None:
            location = next(
                (loc for loc in self.get_locations(include_inactive=True) if loc["id"] == location_id),
                None,
            )
            location_name = location["name"] if location else location_name

        return {
            "location_id": location_id,
            "location_name": location_name,
            "report_month": report_month,
            "new_customers": new_customers,
            "total_customers": total_customers,
        }

    def get_card_counts_by_status(self, location_id: Optional[int] = None) -> list[dict]:
        report = self.get_location_report(location_id)
        return report["card_status_counts"]

    def get_claim_counts_by_status(self, location_id: Optional[int] = None) -> list[dict]:
        report = self.get_location_report(location_id)
        return report["claim_status_counts"]
