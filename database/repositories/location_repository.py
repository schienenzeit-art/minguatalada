from typing import List, Dict, Optional

from database.db import get_connection


class LocationRepository:
    def list_locations(self, include_inactive: bool = False) -> List[Dict[str, object]]:
        with get_connection() as connection:
            if include_inactive:
                rows = connection.execute(
                    "SELECT id, name, is_active FROM locations ORDER BY name"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT id, name, is_active FROM locations WHERE is_active = 1 ORDER BY name"
                ).fetchall()

        return [dict(r) for r in rows]

    def get_location_by_id(self, location_id: int) -> Optional[Dict[str, object]]:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT id, name, is_active FROM locations WHERE id = ?",
                (location_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_location(self, name: str) -> int:
        with get_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO locations (name, is_active) VALUES (?, 1)",
                (name.strip(),),
            )
            connection.commit()
            return cursor.lastrowid

    def update_location(self, location_id: int, name: str) -> bool:
        with get_connection() as connection:
            cursor = connection.execute(
                "UPDATE locations SET name = ? WHERE id = ?",
                (name.strip(), location_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def set_active(self, location_id: int, is_active: bool) -> bool:
        with get_connection() as connection:
            cursor = connection.execute(
                "UPDATE locations SET is_active = ? WHERE id = ?",
                (1 if is_active else 0, location_id),
            )
            connection.commit()
            return cursor.rowcount > 0
