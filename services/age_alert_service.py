"""
20-Jahre-Logik: Wenn ein Kind 20 Jahre alt wird, verliert die gesamte Familie
ab diesem Tag die Anspruchsberechtigung, sofern kein Einkommensnachweis oder
Studentenausweis vorliegt. Supervisor und Dashboard erhalten eine Meldung.
"""
from datetime import date
from typing import Optional

from database.repositories.household_member_repository import HouseholdMemberRepository
from database.db import get_connection


class AgeAlertService:

    WARNING_DAYS = 60  # Warnung 60 Tage vor 20. Geburtstag

    def __init__(self):
        self.hm_repo = HouseholdMemberRepository()

    def get_active_alerts(self) -> list[dict]:
        """Gibt alle aktiven (ungelösten) Alters-Alerts zurück."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT aa.*, hm.first_name AS child_first_name, hm.last_name AS child_last_name,
                       hm.birth_date, cl.case_number,
                       p.first_name AS person_first_name, p.last_name AS person_last_name
                FROM age_alerts aa
                LEFT JOIN household_members hm ON aa.household_member_id = hm.id
                LEFT JOIN claims cl ON aa.claim_id = cl.id
                LEFT JOIN persons p ON cl.person_id = p.id
                WHERE aa.is_resolved = 0
                ORDER BY aa.trigger_date ASC
                """,
            ).fetchall()
        return [dict(r) for r in rows]

    def generate_alerts(self) -> int:
        """
        Prüft alle Kinder und erstellt fehlende Alerts.
        Sollte täglich beim App-Start aufgerufen werden.
        Gibt Anzahl neu erstellter Alerts zurück.
        """
        created = 0

        # Kinder die schon 20 sind (Alert überfällig)
        past = self.hm_repo.get_children_past_age(20)
        for member in past:
            if not self._alert_exists(member["id"], "CHILD_TURNED_20"):
                self._create_alert(
                    claim_id=member["claim_id"],
                    member_id=member["id"],
                    alert_type="CHILD_TURNED_20",
                    trigger_date=member["birth_date"],  # Geburtstag ist Triggerdatum
                    message=(
                        f"{member['first_name']} {member['last_name']} ist bereits 20 Jahre alt. "
                        f"Anspruchsberechtigung der Familie (Fall {member['case_number']}) prüfen. "
                        "Einkommensnachweis oder Studentenausweis anfordern."
                    ),
                )
                created += 1

        # Kinder die in <60 Tagen 20 werden (Vorwarnung)
        approaching = self.hm_repo.get_children_approaching_age(20, self.WARNING_DAYS)
        for member in approaching:
            if not self._alert_exists(member["id"], "CHILD_APPROACHING_20"):
                birthday_20 = self._compute_birthday(member["birth_date"], 20)
                self._create_alert(
                    claim_id=member["claim_id"],
                    member_id=member["id"],
                    alert_type="CHILD_APPROACHING_20",
                    trigger_date=birthday_20 or member["birth_date"],
                    message=(
                        f"{member['first_name']} {member['last_name']} wird bald 20 Jahre alt "
                        f"(Fall {member['case_number']}). "
                        "Einkommen anfragen. Bei keinem Einkommen: Studentenausweis oder anderen Nachweis erbringen lassen."
                    ),
                )
                created += 1

        return created

    def resolve_alert(self, alert_id: int, resolved_by: int) -> bool:
        try:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE age_alerts SET is_resolved=1, resolved_by=?, resolved_at=CURRENT_TIMESTAMP WHERE id=?",
                    (resolved_by, alert_id),
                )
                conn.commit()
            return True
        except Exception:
            return False

    def count_active_alerts(self) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM age_alerts WHERE is_resolved=0"
            ).fetchone()
        return int(row["cnt"]) if row else 0

    def _alert_exists(self, member_id: int, alert_type: str) -> bool:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM age_alerts WHERE household_member_id=? AND alert_type=? AND is_resolved=0",
                (member_id, alert_type),
            ).fetchone()
        return row is not None

    def _create_alert(self, claim_id: int, member_id: int, alert_type: str, trigger_date: str, message: str):
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO age_alerts (claim_id, household_member_id, alert_type, trigger_date, message) VALUES (?,?,?,?,?)",
                (claim_id, member_id, alert_type, trigger_date, message),
            )
            conn.commit()

    @staticmethod
    def _compute_birthday(birth_date_str: str, years: int) -> Optional[str]:
        try:
            bd = date.fromisoformat(birth_date_str)
            return date(bd.year + years, bd.month, bd.day).isoformat()
        except Exception:
            return None
