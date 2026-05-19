from collections import Counter
from typing import Optional

from database.repositories.card_repository import CardRepository
from database.repositories.claim_repository import ClaimRepository
from database.repositories.location_repository import LocationRepository


class ReportService:
    def __init__(
        self,
        location_repository: LocationRepository | None = None,
        claim_repository: ClaimRepository | None = None,
        card_repository: CardRepository | None = None,
    ):
        self.location_repository = location_repository or LocationRepository()
        self.claim_repository = claim_repository or ClaimRepository()
        self.card_repository = card_repository or CardRepository()

    def get_locations(self, include_inactive: bool = False) -> list[dict]:
        return self.location_repository.list_locations(include_inactive=include_inactive)

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

    def get_card_counts_by_status(self, location_id: Optional[int] = None) -> list[dict]:
        report = self.get_location_report(location_id)
        return report["card_status_counts"]

    def get_claim_counts_by_status(self, location_id: Optional[int] = None) -> list[dict]:
        report = self.get_location_report(location_id)
        return report["claim_status_counts"]
