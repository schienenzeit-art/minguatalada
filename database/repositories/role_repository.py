from typing import Dict, List, Optional

from database.db import get_connection


class RoleRepository:
    def list_roles(self, include_inactive: bool = False) -> List[Dict[str, object]]:
        with get_connection() as connection:
            if include_inactive:
                rows = connection.execute(
                    "SELECT id, name, is_active FROM roles ORDER BY name"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT id, name, is_active FROM roles WHERE is_active = 1 ORDER BY name"
                ).fetchall()

        return [dict(r) for r in rows]

    def create_role(self, name: str) -> int:
        with get_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO roles (name, is_active) VALUES (?, 1)",
                (name.strip(),),
            )
            connection.commit()
            return cursor.lastrowid

    def update_role(self, role_id: int, name: str) -> bool:
        with get_connection() as connection:
            cursor = connection.execute(
                "UPDATE roles SET name = ? WHERE id = ?",
                (name.strip(), role_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def set_active(self, role_id: int, is_active: bool) -> bool:
        with get_connection() as connection:
            cursor = connection.execute(
                "UPDATE roles SET is_active = ? WHERE id = ?",
                (1 if is_active else 0, role_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def get_role_by_id(self, role_id: int) -> Optional[Dict[str, object]]:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT id, name, is_active FROM roles WHERE id = ?",
                (role_id,),
            ).fetchone()
        return dict(row) if row else None
