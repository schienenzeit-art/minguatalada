from typing import Optional, Dict, List

from database.db import get_connection


class CaseRepository:
    def create_case(
        self,
        case_number: str,
        person_id: int,
        user_id: int,
        location_id: int,
        category_id: int | None,
        description: str,
        start_date: str | None = None,
        end_date: str | None = None,
        created_by: int | None = None,
    ) -> int:
        with get_connection() as connection:
            # detect table name (claims vs legacy claim)
            tbl = 'claims'
            row = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='claims' LIMIT 1").fetchone()
            if not row:
                row2 = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='claim' LIMIT 1").fetchone()
                if row2:
                    tbl = 'claim'

            cursor = connection.execute(
                f"""
                INSERT INTO {tbl} (
                    case_number, person_id, user_id, location_id, category_id, status, description, start_date, end_date, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_number,
                    person_id,
                    user_id,
                    location_id,
                    category_id,
                    "IN_PRUEFUNG",
                    description,
                    start_date,
                    end_date,
                    created_by,
                ),
            )
            connection.commit()
            return cursor.lastrowid

    def get_case_by_id(self, case_id: int) -> Optional[Dict[str, object]]:
        with get_connection() as connection:
            # detect table name
            tbl = 'claims'
            rowt = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='claims' LIMIT 1").fetchone()
            if not rowt:
                rowt2 = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='claim' LIMIT 1").fetchone()
                if rowt2:
                    tbl = 'claim'

            sql = f"""
                SELECT c.*, p.first_name, p.last_name, cat.name AS category_name, l.name AS location_name
                FROM {tbl} c
                LEFT JOIN persons p ON c.person_id = p.id
                LEFT JOIN categories cat ON c.category_id = cat.id
                LEFT JOIN locations l ON c.location_id = l.id
                WHERE c.id = ?
                """
            row = connection.execute(sql, (case_id,)).fetchone()

        return dict(row) if row else None

    def get_cases(self, location_id: int | None = None) -> List[Dict[str, object]]:
        with get_connection() as connection:
            # detect table name
            tbl = 'claims'
            rowt = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='claims' LIMIT 1").fetchone()
            if not rowt:
                rowt2 = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='claim' LIMIT 1").fetchone()
                if rowt2:
                    tbl = 'claim'

            if location_id:
                rows = connection.execute(
                    f"SELECT * FROM {tbl} WHERE location_id = ? ORDER BY created_at DESC",
                    (location_id,),
                ).fetchall()
            else:
                rows = connection.execute(f"SELECT * FROM {tbl} ORDER BY created_at DESC").fetchall()

        return [dict(r) for r in rows]

    def get_last_case_number_for_year(self, year: int) -> Optional[str]:
        with get_connection() as connection:
            tbl = 'claims'
            row = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='claims' LIMIT 1").fetchone()
            if not row:
                row2 = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='claim' LIMIT 1").fetchone()
                if row2:
                    tbl = 'claim'

            sql = f"SELECT case_number FROM {tbl} WHERE case_number LIKE ? ORDER BY case_number DESC LIMIT 1"
            row = connection.execute(sql, (f"AS-{year}-%",)).fetchone()

        return row["case_number"] if row else None
