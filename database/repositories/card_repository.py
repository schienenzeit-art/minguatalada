from sqlite3 import Row
from typing import Optional
from datetime import datetime

from database.db import get_connection
from core.card_status import CardStatus


class CardRepository:
    """Repository für Kartenverwaltung."""

    def create_card(
        self,
        card_number: str,
        claim_id: int,
        person_id: int,
        location_id: int,
        issue_date: str,
        expiry_date: str,
        created_by: int,
        note: Optional[str] = None,
    ) -> Optional[int]:
        """
        Erstellt eine neue Karte.
        
        Args:
            card_number: Eindeutige Kartennummer (z.B. K-2026-000001)
            claim_id: Zugehöriger Fall
            person_id: Zugehörige Person
            location_id: Standort
            issue_date: Ausstellungsdatum (YYYY-MM-DD)
            expiry_date: Ablaufdatum (YYYY-MM-DD)
            created_by: Benutzer-ID des Erstellers
            note: Optionale Bemerkung
            
        Returns:
            Karten-ID oder None bei Fehler
        """
        try:
            with get_connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO cards (
                        card_number,
                        claim_id,
                        person_id,
                        location_id,
                        issue_date,
                        expiry_date,
                        status,
                        note,
                        created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        card_number,
                        claim_id,
                        person_id,
                        location_id,
                        issue_date,
                        expiry_date,
                        CardStatus.AKTIV,
                        note,
                        created_by,
                    ),
                )
                connection.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Fehler beim Erstellen der Karte: {e}")
            return None

    def get_card_by_id(self, card_id: int) -> Optional[dict]:
        """Holt eine Karte mit allen Details."""
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    c.id,
                    c.card_number,
                    c.claim_id,
                    c.person_id,
                    c.location_id,
                    c.issue_date,
                    c.expiry_date,
                    c.status,
                    c.note,
                    c.created_by,
                    c.created_at,
                    c.updated_at,
                    p.first_name AS person_first_name,
                    p.last_name AS person_last_name,
                    cl.case_number,
                    l.name AS location_name,
                    u.full_name AS creator_name
                FROM cards c
                LEFT JOIN persons p ON c.person_id = p.id
                LEFT JOIN claims cl ON c.claim_id = cl.id
                LEFT JOIN locations l ON c.location_id = l.id
                LEFT JOIN users u ON c.created_by = u.id
                WHERE c.id = ?
                """,
                (card_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def get_cards_by_claim(self, claim_id: int) -> list[dict]:
        """Holt alle Karten für einen Fall."""
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    c.id,
                    c.card_number,
                    c.claim_id,
                    c.person_id,
                    c.location_id,
                    c.issue_date,
                    c.expiry_date,
                    c.status,
                    c.note,
                    c.created_at,
                    p.first_name AS person_first_name,
                    p.last_name AS person_last_name,
                    l.name AS location_name
                FROM cards c
                LEFT JOIN persons p ON c.person_id = p.id
                LEFT JOIN locations l ON c.location_id = l.id
                WHERE c.claim_id = ?
                ORDER BY c.created_at DESC
                """,
                (claim_id,),
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_cards_by_person(self, person_id: int) -> list[dict]:
        """Holt alle Karten für eine Person."""
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    c.id,
                    c.card_number,
                    c.claim_id,
                    c.person_id,
                    c.location_id,
                    c.issue_date,
                    c.expiry_date,
                    c.status,
                    c.created_at,
                    cl.case_number,
                    l.name AS location_name
                FROM cards c
                LEFT JOIN claims cl ON c.claim_id = cl.id
                LEFT JOIN locations l ON c.location_id = l.id
                WHERE c.person_id = ?
                ORDER BY c.created_at DESC
                """,
                (person_id,),
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_cards(
        self,
        location_id: Optional[int] = None,
        status: Optional[str] = None,
        person_id: Optional[int] = None,
        search_text: Optional[str] = None,
    ) -> list[dict]:
        """
        Holt Karten mit optionalen Filtern.
        
        Args:
            location_id: Filter nach Standort
            status: Filter nach Status
            person_id: Filter nach Person
            search_text: Suche in Kartennummer und Person
        """
        query = [
            "SELECT",
            "    c.id,",
            "    c.card_number,",
            "    c.claim_id,",
            "    c.person_id,",
            "    c.location_id,",
            "    c.issue_date,",
            "    c.expiry_date,",
            "    c.status,",
            "    c.created_at,",
            "    p.first_name AS person_first_name,",
            "    p.last_name AS person_last_name,",
            "    cl.case_number,",
            "    l.name AS location_name",
            "FROM cards c",
            "LEFT JOIN persons p ON c.person_id = p.id",
            "LEFT JOIN claims cl ON c.claim_id = cl.id",
            "LEFT JOIN locations l ON c.location_id = l.id",
            "WHERE 1=1",
        ]

        params: list = []

        if location_id is not None:
            query.append("AND c.location_id = ?")
            params.append(location_id)

        if status is not None:
            query.append("AND c.status = ?")
            params.append(status)

        if person_id is not None:
            query.append("AND c.person_id = ?")
            params.append(person_id)

        if search_text:
            query.append("AND (c.card_number LIKE ? OR p.first_name LIKE ? OR p.last_name LIKE ?)")
            search_pattern = f"%{search_text}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        query.extend([
            "ORDER BY c.created_at DESC",
        ])

        sql = " ".join(query)

        with get_connection() as connection:
            rows = connection.execute(sql, params).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def count_cards(
        self,
        status: str | None = None,
        statuses: list[str] | None = None,
        location_id: int | None = None,
        issued_from: str | None = None,
        issued_to: str | None = None,
    ) -> int:
        query = ["SELECT COUNT(*) AS total FROM cards c"]
        params: list = []
        filters: list[str] = []

        if location_id is not None:
            filters.append("c.location_id = ?")
            params.append(location_id)

        if statuses:
            filters.append(f"c.status IN ({','.join(['?'] * len(statuses))})")
            params.extend(statuses)
        elif status is not None:
            filters.append("c.status = ?")
            params.append(status)

        if issued_from is not None:
            filters.append("DATE(c.issue_date) >= DATE(?)")
            params.append(issued_from)

        if issued_to is not None:
            filters.append("DATE(c.issue_date) <= DATE(?)")
            params.append(issued_to)

        if filters:
            query.append("WHERE " + " AND ".join(filters))

        sql = " ".join(query)

        with get_connection() as connection:
            row = connection.execute(sql, tuple(params)).fetchone()

        return int(row["total"] if row else 0)

    def count_cards_by_location(
        self,
        location_id: int | None = None,
        issued_from: str | None = None,
        issued_to: str | None = None,
    ) -> list[dict]:
        query = [
            "SELECT",
            "    l.id AS location_id,",
            "    COALESCE(l.name, 'Unbekannt') AS location_name,",
            "    COUNT(c.id) AS card_count",
            "FROM cards c",
            "LEFT JOIN locations l ON c.location_id = l.id",
        ]
        params: list[object] = []
        filters: list[str] = []

        if location_id is not None:
            filters.append("c.location_id = ?")
            params.append(location_id)

        if issued_from is not None:
            filters.append("DATE(c.issue_date) >= DATE(?)")
            params.append(issued_from)

        if issued_to is not None:
            filters.append("DATE(c.issue_date) <= DATE(?)")
            params.append(issued_to)

        if filters:
            query.append("WHERE " + " AND ".join(filters))

        query.extend([
            "GROUP BY l.id, l.name",
            "ORDER BY l.name ASC",
        ])

        sql = "\n".join(query)
        with get_connection() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def count_expiring_cards(self, days: int = 30) -> int:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM cards c
                WHERE c.status != ?
                AND DATE(c.expiry_date) <= DATE('now', '+' || ? || ' days')
                AND DATE(c.expiry_date) >= DATE('now')
                """,
                (CardStatus.ARCHIVIERT, days),
            ).fetchone()

        return int(row["total"] if row else 0)

    def update_card_status(self, card_id: int, status: str) -> bool:
        """Aktualisiert den Status einer Karte."""
        if not CardStatus.is_valid_status(status):
            return False

        try:
            with get_connection() as connection:
                cursor = connection.execute(
                    "UPDATE cards SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, card_id),
                )
                connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Fehler beim Aktualisieren des Kartenstatus: {e}")
            return False

    def update_card_status_with_reason(self, card_id: int, status: str, block_reason: str | None = None) -> bool:
        if not CardStatus.is_valid_status(status):
            return False
        try:
            with get_connection() as connection:
                cursor = connection.execute(
                    "UPDATE cards SET status = ?, block_reason = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, block_reason, card_id),
                )
                connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Fehler beim Aktualisieren des Kartenstatus: {e}")
            return False

    def get_card_stats_by_location(self, location_id: int | None = None) -> dict:
        params: list = []
        where = "WHERE 1=1"
        if location_id is not None:
            where += " AND c.location_id = ?"
            params.append(location_id)
        with get_connection() as connection:
            rows = connection.execute(
                f"SELECT c.status, COUNT(*) AS cnt FROM cards c {where} GROUP BY c.status",
                params,
            ).fetchall()
        stats: dict = {}
        for r in rows:
            stats[r["status"]] = r["cnt"]
        return stats

    # Nummernkreise nach Standort (Anforderung 5)
    # Bludenz: 10001–19999, Feldkirch: 20001–29999, Dornbirn: 30001–39999
    # Personal/Freiwillige: 8001–8999
    LOCATION_RANGES: dict[str, tuple[int, int]] = {
        "Bludenz":   (10001, 19999),
        "Feldkirch": (20001, 29999),
        "Dornbirn":  (30001, 39999),
    }
    STAFF_RANGE_START = 8001
    STAFF_RANGE_END   = 8999

    def get_next_card_number(
        self,
        location_name: str | None = None,
        is_staff: bool = False,
    ) -> str:
        """
        Generiert die nächste Kartennummer gemäß Nummernkreis-Logik.

        Nummernkreise:
          Bludenz   → 10001–19999
          Feldkirch → 20001–29999
          Dornbirn  → 30001–39999
          Personal/Freiwillige → 8001–8999

        HINWEIS zu "8001": Alle Personal-/Freiwilligen-Karten liegen im Bereich
        ab 8001. Es gibt NICHT alle dieselbe Nummer – jede Karte erhält eine
        eigene Nummer in diesem Bereich. Sollte fachlich eine Einzelnummer
        gewünscht sein, hier anpassen.
        """
        with get_connection() as connection:
            if is_staff:
                start = self.STAFF_RANGE_START
                end   = self.STAFF_RANGE_END
                pattern = f"{start // 1000}%"
                last = connection.execute(
                    "SELECT card_number FROM cards WHERE CAST(card_number AS INTEGER) >= ? AND CAST(card_number AS INTEGER) <= ? ORDER BY CAST(card_number AS INTEGER) DESC LIMIT 1",
                    (start, end),
                ).fetchone()
                if last and last[0]:
                    try:
                        next_num = int(last[0]) + 1
                    except ValueError:
                        next_num = start
                else:
                    next_num = start
                if next_num > end:
                    raise ValueError(f"Nummernkreis Personal ({start}–{end}) erschöpft")
                return str(next_num)

            if location_name and location_name in self.LOCATION_RANGES:
                start, end = self.LOCATION_RANGES[location_name]
                last = connection.execute(
                    "SELECT card_number FROM cards WHERE CAST(card_number AS INTEGER) >= ? AND CAST(card_number AS INTEGER) <= ? ORDER BY CAST(card_number AS INTEGER) DESC LIMIT 1",
                    (start, end),
                ).fetchone()
                if last and last[0]:
                    try:
                        next_num = int(last[0]) + 1
                    except ValueError:
                        next_num = start
                else:
                    next_num = start
                if next_num > end:
                    raise ValueError(f"Nummernkreis {location_name} ({start}–{end}) erschöpft")
                return str(next_num)

            # Fallback für unbekannte Standorte: altes Format
            year = datetime.now().year
            last = connection.execute(
                "SELECT card_number FROM cards WHERE card_number LIKE ? ORDER BY card_number DESC LIMIT 1",
                (f"K-{year}-%",),
            ).fetchone()
            if last and last[0]:
                try:
                    seq = int(last[0].split("-")[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1
            return f"K-{year}-{seq:06d}"

    def check_and_update_expiry_status(self, card_id: int, days_threshold: int = 30) -> str:
        """
        Prüft und aktualisiert den Kartenstatus basierend auf Ablaufdatum.
        
        Returns: Aktueller Status nach Prüfung
        """
        card = self.get_card_by_id(card_id)
        if not card:
            return CardStatus.ARCHIVIERT

        if card["status"] in [CardStatus.GESPERRT, CardStatus.ARCHIVIERT]:
            return card["status"]

        try:
            expiry = datetime.strptime(card["expiry_date"], "%Y-%m-%d").date()
            today = datetime.now().date()

            if today > expiry:
                new_status = CardStatus.ABGELAUFEN
            elif (expiry - today).days <= days_threshold:
                new_status = CardStatus.BALD_ABLAUFEND
            else:
                new_status = CardStatus.AKTIV

            if card["status"] != new_status:
                self.update_card_status(card_id, new_status)

            return new_status
        except Exception as e:
            print(f"Fehler bei Ablauf-Prüfung: {e}")
            return card["status"]

    def get_expiring_cards(self, days: int = 30) -> list[dict]:
        """Holt alle Karten die in den nächsten Tagen ablaufen."""
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    c.id,
                    c.card_number,
                    c.person_id,
                    c.expiry_date,
                    c.status,
                    p.first_name AS person_first_name,
                    p.last_name AS person_last_name,
                    l.name AS location_name
                FROM cards c
                LEFT JOIN persons p ON c.person_id = p.id
                LEFT JOIN locations l ON c.location_id = l.id
                WHERE c.status != ?
                AND DATE(c.expiry_date) <= DATE('now', '+' || ? || ' days')
                AND DATE(c.expiry_date) >= DATE('now')
                ORDER BY c.expiry_date ASC
                """,
                (CardStatus.ARCHIVIERT, days),
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: Row) -> dict:
        """Konvertiert eine Datenbankzeile zu dict."""
        return dict(row) if row else {}
