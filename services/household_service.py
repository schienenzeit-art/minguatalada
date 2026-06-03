"""
Haushaltsverwaltung: Haushaltsmitglieder anlegen, bearbeiten, Familienzuwachs erfassen.
Alle Änderungen werden im AuditLog erfasst.
"""
from typing import Optional

from database.repositories.household_member_repository import HouseholdMemberRepository
from database.repositories.audit_repository import AuditRepository
from core.session import Session


class HouseholdService:

    RELATIONSHIPS = [
        "Hauptantragsteller",
        "Ehepartner",
        "Lebenspartner",
        "Kind",
        "Stiefkind",
        "Pflegekind",
        "Elternteil",
        "Geschwister",
        "Sonstiges",
    ]

    def __init__(self):
        self.hm_repo = HouseholdMemberRepository()
        self.audit_repo = AuditRepository()

    def get_members(self, claim_id: int) -> list[dict]:
        return self.hm_repo.get_members_for_claim(claim_id)

    def add_member(
        self,
        claim_id: int,
        first_name: str,
        last_name: str,
        birth_date: Optional[str],
        relationship: str,
        is_primary: bool = False,
        category_id: Optional[int] = None,
    ) -> Optional[int]:
        member_id = self.hm_repo.add_member(
            claim_id=claim_id,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            relationship=relationship,
            is_primary=is_primary,
            category_id=category_id,
        )
        if member_id:
            self.audit_repo.log(
                user_id=Session.get_user_id(),
                action="HAUSHALT_MITGLIED_HINZUGEFUEGT",
                object_type="household_member",
                object_id=member_id,
                details=f"Fall {claim_id}: {first_name} {last_name} ({relationship}) hinzugefügt",
            )
        return member_id

    def update_member(
        self,
        member_id: int,
        first_name: str,
        last_name: str,
        birth_date: Optional[str],
        relationship: str,
        category_id: Optional[int] = None,
    ) -> bool:
        result = self.hm_repo.update_member(
            member_id, first_name, last_name, birth_date, relationship, category_id
        )
        if result:
            self.audit_repo.log(
                user_id=Session.get_user_id(),
                action="HAUSHALT_MITGLIED_AKTUALISIERT",
                object_type="household_member",
                object_id=member_id,
                details=f"{first_name} {last_name} ({relationship}) aktualisiert",
            )
        return result

    def remove_member(self, member_id: int) -> bool:
        member = self.hm_repo.get_member(member_id)
        result = self.hm_repo.delete_member(member_id)
        if result and member:
            self.audit_repo.log(
                user_id=Session.get_user_id(),
                action="HAUSHALT_MITGLIED_ENTFERNT",
                object_type="household_member",
                object_id=member_id,
                details=f"{member.get('first_name','?')} {member.get('last_name','?')} entfernt",
            )
        return result

    def add_family_member(
        self,
        claim_id: int,
        first_name: str,
        last_name: str,
        birth_date: Optional[str],
        relationship: str,
    ) -> Optional[int]:
        """Familienzuwachs: neue Person zu bestehendem Fall hinzufügen."""
        return self.add_member(
            claim_id=claim_id,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            relationship=relationship,
        )

    def get_relationships(self) -> list[str]:
        return self.RELATIONSHIPS
