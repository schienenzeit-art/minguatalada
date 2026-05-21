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

    def get_person_by_id(self, person_id: int) -> Optional[Dict[str, object]]:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM persons WHERE id = ?",
                (person_id,),
            ).fetchone()

        if not row:
            return None

        return dict(row)

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
