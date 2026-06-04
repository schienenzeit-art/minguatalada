from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ClaimSnapshot:
    """Unveränderlicher Schnappschuss eines Antrags – typsicherer Ersatz für rohe dicts."""

    id: int
    case_number: str
    status: str
    location_id: int
    evaluation_count: int
    person_id: Optional[int] = None
    location_name: Optional[str] = None
    user_id: Optional[int] = None
    description: Optional[str] = None
    category: Optional[str] = None
    category_id: Optional[int] = None
    adult_count: int = 1
    child_count: int = 0
    disability_degree: Optional[int] = None
    has_housing_benefit: Optional[bool] = None
    examiner_name: Optional[str] = None
    first_examiner_id: Optional[int] = None
    widerspruch_frist: Optional[str] = None
    review_date: Optional[str] = None
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "ClaimSnapshot":
        raw_hwb = d.get("has_housing_benefit")
        has_hwb = bool(raw_hwb) if raw_hwb is not None else None
        return cls(
            id=d["id"],
            case_number=d["case_number"],
            status=d["status"],
            location_id=d["location_id"],
            evaluation_count=d.get("evaluation_count") or 0,
            person_id=d.get("person_id"),
            location_name=d.get("location_name"),
            user_id=d.get("user_id"),
            description=d.get("description"),
            category=d.get("category"),
            category_id=d.get("category_id"),
            adult_count=d.get("adult_count") or 1,
            child_count=d.get("child_count") or 0,
            disability_degree=d.get("disability_degree"),
            has_housing_benefit=has_hwb,
            examiner_name=d.get("examiner_name"),
            first_examiner_id=d.get("first_examiner_id"),
            widerspruch_frist=d.get("widerspruch_frist"),
            review_date=d.get("review_date"),
            created_at=d.get("created_at"),
        )
