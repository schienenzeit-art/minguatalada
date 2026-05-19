import json
from sqlite3 import Row
from typing import Optional

from core.claim_status import ClaimStatus
from database.db import get_connection


class ClaimRepository:
    def _table_name(self, connection) -> str:
        # prefer 'claims', fall back to 'claim' if present
        tbl = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='claims' LIMIT 1").fetchone()
        if tbl:
            return 'claims'
        tbl2 = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='claim' LIMIT 1").fetchone()
        if tbl2:
            return 'claim'
        return 'claims'

    def get_claim_by_id(self, claim_id: int) -> Optional[dict]:
        with get_connection() as connection:
            tbl = self._table_name(connection)
            sql = f"""
                SELECT
                    c.id,
                    c.case_number,
                    c.description,
                    c.status,
                    c.start_date,
                    c.end_date,
                    c.created_at,
                    c.updated_at,
                    u.id AS user_id,
                    u.full_name AS user_name,
                    l.id AS location_id,
                    l.name AS location_name,
                    p.id AS person_id,
                    p.first_name AS person_first_name,
                    p.last_name AS person_last_name,
                    p.address AS person_address,
                    p.postal_code AS person_postal_code,
                    p.city AS person_city,
                    p.email AS person_email,
                    cat.name AS category_name,
                    c.adult_count,
                    c.child_count,
                    c.disability_degree,
                    c.evaluation_reason,
                    c.total_income,
                    c.total_expenses,
                    c.free_income,
                    c.entitlement_limit,
                    c.hardship_limit,
                    c.evaluation_details,
                    c.examiner_id,
                    e.full_name AS examiner_name,
                    c.evaluation_date
                FROM {tbl} c
                JOIN users u ON c.user_id = u.id
                LEFT JOIN users e ON c.examiner_id = e.id
                LEFT JOIN locations l ON c.location_id = l.id
                LEFT JOIN persons p ON c.person_id = p.id
                LEFT JOIN categories cat ON c.category_id = cat.id
                WHERE c.id = ?
                """

            row = connection.execute(sql, (claim_id,)).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def update_claim_status(self, claim_id: int, status: str) -> bool:
        if not ClaimStatus.is_valid_status(status):
            return False

        with get_connection() as connection:
            tbl = self._table_name(connection)
            sql = f"UPDATE {tbl} SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            cursor = connection.execute(sql, (status, claim_id))
            connection.commit()

        return cursor.rowcount > 0

    def get_claims(
        self,
        location_id: int | None = None,
        status: str | None = None,
        category_id: int | None = None,
        examiner_id: int | None = None,
        search_text: str | None = None,
    ) -> list[dict]:
        with get_connection() as connection:
            tbl = self._table_name(connection)
            query = [
                "SELECT",
                "    c.id,",
                "    c.case_number,",
                "    c.description,",
                "    c.status,",
                "    c.start_date,",
                "    c.end_date,",
                "    c.created_at,",
                "    c.updated_at,",
                "    u.id AS user_id,",
                "    u.full_name AS user_name,",
                "    e.id AS examiner_id,",
                "    e.full_name AS examiner_name,",
                "    l.id AS location_id,",
                "    l.name AS location_name,",
                "    p.first_name AS person_first_name,",
                "    p.last_name AS person_last_name,",
                "    cat.id AS category_id,",
                "    cat.name AS category_name",
                f"FROM {tbl} c",
                "JOIN users u ON c.user_id = u.id",
                "LEFT JOIN users e ON c.examiner_id = e.id",
                "LEFT JOIN locations l ON c.location_id = l.id",
                "LEFT JOIN persons p ON c.person_id = p.id",
                "LEFT JOIN categories cat ON c.category_id = cat.id",
            ]
            params: list[object] = []
            filters: list[str] = []

            if location_id is not None:
                filters.append("c.location_id = ?")
                params.append(location_id)

            if status:
                filters.append("c.status = ?")
                params.append(status)

            if category_id is not None:
                filters.append("c.category_id = ?")
                params.append(category_id)

            if examiner_id is not None:
                filters.append("c.examiner_id = ?")
                params.append(examiner_id)

            if search_text:
                search = f"%{search_text.strip().lower()}%"
                filters.append(
                    "(LOWER(c.case_number) LIKE ? OR LOWER(p.first_name || ' ' || p.last_name) LIKE ? OR LOWER(p.last_name || ' ' || p.first_name) LIKE ? )"
                )
                params.extend([search, search, search])

            if filters:
                query.append("WHERE " + " AND ".join(filters))

            query.append("ORDER BY c.created_at DESC")
            sql = "\n".join(query)

            rows = connection.execute(sql, tuple(params)).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def count_claims(
        self,
        status: str | None = None,
        statuses: list[str] | None = None,
        location_id: int | None = None,
        category_id: int | None = None,
        examiner_id: int | None = None,
        start_date: str | None = None,
        created_since_days: int | None = None,
    ) -> int:
        with get_connection() as connection:
            tbl = self._table_name(connection)
            query = [f"SELECT COUNT(*) AS total FROM {tbl} c"]
            params: list[object] = []
            filters: list[str] = []

            if location_id is not None:
                filters.append("c.location_id = ?")
                params.append(location_id)

            if category_id is not None:
                filters.append("c.category_id = ?")
                params.append(category_id)

            if examiner_id is not None:
                filters.append("c.examiner_id = ?")
                params.append(examiner_id)

            if statuses:
                filters.append(f"c.status IN ({','.join(['?'] * len(statuses))})")
                params.extend(statuses)
            elif status:
                filters.append("c.status = ?")
                params.append(status)

            if start_date:
                filters.append("DATE(c.start_date) = DATE(?)")
                params.append(start_date)

            if created_since_days is not None:
                filters.append("DATE(c.created_at) >= DATE('now', ?)")
                params.append(f"-{created_since_days} days")

            if filters:
                query.append("WHERE " + " AND ".join(filters))

            sql = " ".join(query)
            row = connection.execute(sql, tuple(params)).fetchone()

        return int(row["total"] if row else 0)

    def _row_to_dict(self, row: Row) -> dict:
        person_first = row["person_first_name"] if "person_first_name" in row.keys() else None
        person_last = row["person_last_name"] if "person_last_name" in row.keys() else None
        if person_last and person_first:
            person_display_name = f"{person_last}, {person_first}"
        elif person_first:
            person_display_name = person_first
        elif person_last:
            person_display_name = person_last
        else:
            person_display_name = row["user_name"] if "user_name" in row.keys() else None

        evaluation_details = None
        if "evaluation_details" in row.keys() and row["evaluation_details"]:
            try:
                evaluation_details = json.loads(row["evaluation_details"])
            except Exception:
                evaluation_details = row["evaluation_details"]

        return {
            "id": row["id"],
            "description": row["description"],
            "status": row["status"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "user_id": row["user_id"],
            "user_name": row["user_name"],
            "examiner_id": row["examiner_id"] if "examiner_id" in row.keys() else None,
            "examiner_name": row["examiner_name"] if "examiner_name" in row.keys() else None,
            "evaluation_date": row["evaluation_date"] if "evaluation_date" in row.keys() else None,
            "location_id": row["location_id"],
            "location_name": row["location_name"],
            "person_id": row["person_id"] if "person_id" in row.keys() else None,
            "person_first_name": person_first,
            "person_last_name": person_last,
            "person_address": row["person_address"] if "person_address" in row.keys() else None,
            "person_postal_code": row["person_postal_code"] if "person_postal_code" in row.keys() else None,
            "person_city": row["person_city"] if "person_city" in row.keys() else None,
            "person_email": row["person_email"] if "person_email" in row.keys() else None,
            "person_display_name": person_display_name,
            "case_number": row["case_number"] if "case_number" in row.keys() else None,
            "category_id": row["category_id"] if "category_id" in row.keys() else None,
            "category_name": row["category_name"] if "category_name" in row.keys() else None,
            "examiner_id": row["examiner_id"] if "examiner_id" in row.keys() else None,
            "examiner_name": row["examiner_name"] if "examiner_name" in row.keys() else None,
            "adult_count": row["adult_count"] if "adult_count" in row.keys() else None,
            "child_count": row["child_count"] if "child_count" in row.keys() else None,
            "disability_degree": row["disability_degree"] if "disability_degree" in row.keys() else None,
            "evaluation_reason": row["evaluation_reason"] if "evaluation_reason" in row.keys() else None,
            "total_income": row["total_income"] if "total_income" in row.keys() else None,
            "total_expenses": row["total_expenses"] if "total_expenses" in row.keys() else None,
            "free_income": row["free_income"] if "free_income" in row.keys() else None,
            "entitlement_limit": row["entitlement_limit"] if "entitlement_limit" in row.keys() else None,
            "hardship_limit": row["hardship_limit"] if "hardship_limit" in row.keys() else None,
            "evaluation_details": evaluation_details,
        }

    def update_claim_evaluation(
        self,
        claim_id: int,
        status: str | None = None,
        adult_count: int | None = None,
        child_count: int | None = None,
        disability_degree: int | None = None,
        evaluation_reason: str | None = None,
        total_income: float | None = None,
        total_expenses: float | None = None,
        free_income: float | None = None,
        entitlement_limit: float | None = None,
        hardship_limit: float | None = None,
        evaluation_details: dict | None = None,
        examiner_id: int | None = None,
        evaluation_date: str | None = None,
    ) -> bool:
        parts = []
        params: list[object] = []
        if status is not None:
            parts.append("status = ?")
            params.append(status)
        if adult_count is not None:
            parts.append("adult_count = ?")
            params.append(adult_count)
        if child_count is not None:
            parts.append("child_count = ?")
            params.append(child_count)
        if disability_degree is not None:
            parts.append("disability_degree = ?")
            params.append(disability_degree)
        if evaluation_reason is not None:
            parts.append("evaluation_reason = ?")
            params.append(evaluation_reason)
        if total_income is not None:
            parts.append("total_income = ?")
            params.append(total_income)
        if total_expenses is not None:
            parts.append("total_expenses = ?")
            params.append(total_expenses)
        if free_income is not None:
            parts.append("free_income = ?")
            params.append(free_income)
        if entitlement_limit is not None:
            parts.append("entitlement_limit = ?")
            params.append(entitlement_limit)
        if hardship_limit is not None:
            parts.append("hardship_limit = ?")
            params.append(hardship_limit)
        if evaluation_details is not None:
            parts.append("evaluation_details = ?")
            params.append(json.dumps(evaluation_details, ensure_ascii=False))
        if examiner_id is not None:
            parts.append("examiner_id = ?")
            params.append(examiner_id)
        if evaluation_date is not None:
            parts.append("evaluation_date = ?")
            params.append(evaluation_date)

        if not parts:
            return False

        params.append(claim_id)
        with get_connection() as connection:
            tbl = self._table_name(connection)
            sql = f"UPDATE {tbl} SET {', '.join(parts)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            cursor = connection.execute(sql, tuple(params))
            connection.commit()

        return cursor.rowcount > 0
