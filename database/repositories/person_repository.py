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
