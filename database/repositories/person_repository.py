from typing import Optional, Dict

from database.db import get_connection


class PersonRepository:
    def create_person(self, person: Dict[str, object]) -> int:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO persons (
                    first_name, last_name, address, postal_code, city, email, category_id, location_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    person.get("first_name"),
                    person.get("last_name"),
                    person.get("address"),
                    person.get("postal_code"),
                    person.get("city"),
                    person.get("email"),
                    person.get("category_id"),
                    person.get("location_id"),
                ),
            )
            connection.commit()
            return cursor.lastrowid

    def update_person(self, person_id: int, data: Dict[str, object]) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE persons
                SET first_name = ?, last_name = ?, address = ?, postal_code = ?, city = ?, email = ?
                WHERE id = ?
                """,
                (
                    data.get("first_name"),
                    data.get("last_name"),
                    data.get("address"),
                    data.get("postal_code"),
                    data.get("city"),
                    data.get("email"),
                    person_id,
                ),
            )
            connection.commit()

    def get_person_by_id(self, person_id: int) -> Optional[Dict[str, object]]:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM persons WHERE id = ?",
                (person_id,),
            ).fetchone()

        if not row:
            return None

        return dict(row)

    def list_persons(
        self,
        last_name: str | None = None,
        first_name: str | None = None,
        location_id: int | None = None,
        latest_claim_status: str | None = None,
    ) -> list[dict]:
        with get_connection() as connection:
            query = [
                "SELECT p.id, p.first_name, p.last_name, p.address, p.postal_code, p.city, p.email, p.created_at,",
                "c.name AS category_name, l.name AS location_name,",
                "(SELECT status FROM claims WHERE person_id = p.id ORDER BY created_at DESC LIMIT 1) AS latest_claim_status,",
                "(SELECT COUNT(*) FROM claims WHERE person_id = p.id) AS claim_count",
                "FROM persons p",
                "LEFT JOIN categories c ON p.category_id = c.id",
                "LEFT JOIN locations l ON p.location_id = l.id",
            ]
            params: list[object] = []
            filters: list[str] = []

            if last_name:
                filters.append("LOWER(p.last_name) LIKE ?")
                params.append(f"%{last_name.strip().lower()}%")

            if first_name:
                filters.append("LOWER(p.first_name) LIKE ?")
                params.append(f"%{first_name.strip().lower()}%")

            if location_id is not None:
                filters.append("p.location_id = ?")
                params.append(location_id)

            if latest_claim_status is not None:
                if latest_claim_status == "KEIN_FALL":
                    filters.append("(SELECT status FROM claims WHERE person_id = p.id ORDER BY created_at DESC LIMIT 1) IS NULL")
                else:
                    filters.append("(SELECT status FROM claims WHERE person_id = p.id ORDER BY created_at DESC LIMIT 1) = ?")
                    params.append(latest_claim_status)

            if filters:
                query.append("WHERE " + " AND ".join(filters))

            query.append("ORDER BY p.last_name, p.first_name")
            sql = " ".join(query)
            rows = connection.execute(sql, tuple(params)).fetchall()

        return [dict(row) for row in rows]

    def count_persons(
        self,
        location_id: int | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> int:
        with get_connection() as connection:
            query = ["SELECT COUNT(*) AS total FROM persons"]
            params: list[object] = []
            filters: list[str] = []

            if location_id is not None:
                filters.append("location_id = ?")
                params.append(location_id)

            if created_from is not None:
                filters.append("DATE(created_at) >= DATE(?)")
                params.append(created_from)

            if created_to is not None:
                filters.append("DATE(created_at) <= DATE(?)")
                params.append(created_to)

            if filters:
                query.append("WHERE " + " AND ".join(filters))

            sql = " ".join(query)
            row = connection.execute(sql, tuple(params)).fetchone()

        return int(row["total"] if row else 0)
