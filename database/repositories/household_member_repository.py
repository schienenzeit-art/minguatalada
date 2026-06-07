from typing import Optional

from database.db import get_connection


class HouseholdMemberRepository:
    """Verwaltet Haushaltsmitglieder (Erwachsene und Kinder) eines Falls."""

    def add_member(
        self,
        claim_id: int,
        first_name: str,
        last_name: str,
        birth_date: Optional[str],
        relationship: str,
        is_primary: bool = False,
        person_id: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> Optional[int]:
        try:
            with get_connection() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO household_members
                        (claim_id, person_id, first_name, last_name, birth_date,
                         relationship, is_primary, category_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (claim_id, person_id, first_name, last_name, birth_date,
                     relationship, 1 if is_primary else 0, category_id),
                )
                conn.commit()
                return cur.lastrowid
        except Exception as e:
            print(f"Fehler beim Anlegen des Haushaltsmitglieds: {e}")
            return None

    def get_members_for_claim(self, claim_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT hm.id, hm.claim_id, hm.person_id, hm.first_name, hm.last_name,
                       hm.birth_date, hm.relationship, hm.is_primary, hm.created_at,
                       hm.category_id, c.name AS category_name
                FROM household_members hm
                LEFT JOIN categories c ON hm.category_id = c.id
                WHERE hm.claim_id = ?
                ORDER BY hm.is_primary DESC, hm.last_name ASC, hm.first_name ASC
                """,
                (claim_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_member(self, member_id: int) -> Optional[dict]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT hm.*, c.name AS category_name
                FROM household_members hm
                LEFT JOIN categories c ON hm.category_id = c.id
                WHERE hm.id = ?
                """,
                (member_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_member(
        self,
        member_id: int,
        first_name: str,
        last_name: str,
        birth_date: Optional[str],
        relationship: str,
        category_id: Optional[int] = None,
    ) -> bool:
        try:
            with get_connection() as conn:
                cur = conn.execute(
                    """
                    UPDATE household_members
                    SET first_name=?, last_name=?, birth_date=?, relationship=?,
                        category_id=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (first_name, last_name, birth_date, relationship, category_id, member_id),
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"Fehler beim Aktualisieren: {e}")
            return False

    def delete_member(self, member_id: int) -> bool:
        try:
            with get_connection() as conn:
                cur = conn.execute("DELETE FROM household_members WHERE id=?", (member_id,))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"Fehler beim Löschen: {e}")
            return False

    def get_children_approaching_age(self, threshold_years: int = 20, warning_days: int = 60) -> list[dict]:
        """Gibt alle Kinder zurück, die in warning_days Tagen threshold_years Jahre alt werden."""
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT hm.*, cl.case_number, cl.status AS claim_status,
                       cl.id AS claim_id_ref,
                       p.first_name AS person_first_name, p.last_name AS person_last_name
                FROM household_members hm
                JOIN claims cl ON hm.claim_id = cl.id
                LEFT JOIN persons p ON cl.person_id = p.id
                WHERE hm.relationship IN ('Kind', 'Stiefkind', 'Pflegekind')
                  AND hm.birth_date IS NOT NULL
                  AND DATE(hm.birth_date, '+{threshold_years} years') BETWEEN DATE('now') AND DATE('now', '+{warning_days} days')
                  AND cl.status NOT IN ('ARCHIVIERT', 'ABGELEHNT', 'ABGELAUFEN')
                ORDER BY hm.birth_date ASC
                """,
            ).fetchall()
        return [dict(r) for r in rows]

    def get_children_past_age(self, threshold_years: int = 20) -> list[dict]:
        """Gibt alle Kinder zurück, die threshold_years schon überschritten haben (ungelöste Alerts)."""
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT hm.*, cl.case_number, cl.status AS claim_status,
                       cl.id AS claim_id_ref,
                       p.first_name AS person_first_name, p.last_name AS person_last_name
                FROM household_members hm
                JOIN claims cl ON hm.claim_id = cl.id
                LEFT JOIN persons p ON cl.person_id = p.id
                WHERE hm.relationship IN ('Kind', 'Stiefkind', 'Pflegekind')
                  AND hm.birth_date IS NOT NULL
                  AND DATE(hm.birth_date, '+{threshold_years} years') <= DATE('now')
                  AND cl.status NOT IN ('ARCHIVIERT', 'ABGELEHNT', 'ABGELAUFEN')
                ORDER BY hm.birth_date ASC
                """,
            ).fetchall()
        return [dict(r) for r in rows]
