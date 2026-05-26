from sqlite3 import Row
from typing import Optional

from database.db import get_connection


class UserRepository:

    def get_by_username(self, username: str) -> Optional[dict]:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    u.id,
                    u.full_name,
                    u.username,
                    u.password_hash,
                    u.is_active,
                    u.failed_attempts,
                    u.locked_until,
                    r.name AS role_name,
                    l.id AS location_id,
                    l.name AS location_name
                FROM users u
                JOIN roles r ON u.role_id = r.id
                LEFT JOIN locations l ON u.location_id = l.id
                WHERE u.username = ?
                """,
                (username,)
            ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def get_all(self) -> list[dict]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    u.id,
                    u.full_name,
                    u.username,
                    u.password_hash,
                    u.is_active,
                    u.failed_attempts,
                    u.locked_until,
                    r.name AS role_name,
                    l.id AS location_id,
                    l.name AS location_name
                FROM users u
                JOIN roles r ON u.role_id = r.id
                LEFT JOIN locations l ON u.location_id = l.id
                ORDER BY u.full_name
                """
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_roles(self) -> list[dict]:
        with get_connection() as connection:
            rows = connection.execute("SELECT id, name FROM roles ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def get_locations(self) -> list[dict]:
        with get_connection() as connection:
            rows = connection.execute("SELECT id, name FROM locations ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def get_users_by_location_id(self, location_id: int | None = None) -> list[dict]:
        with get_connection() as connection:
            if location_id is None:
                rows = connection.execute(
                    """
                    SELECT
                        u.id,
                        u.full_name,
                        u.username,
                        u.password_hash,
                        u.is_active,
                        u.failed_attempts,
                        u.locked_until,
                        r.name AS role_name,
                        l.id AS location_id,
                        l.name AS location_name
                    FROM users u
                    JOIN roles r ON u.role_id = r.id
                    LEFT JOIN locations l ON u.location_id = l.id
                    ORDER BY u.full_name
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT
                        u.id,
                        u.full_name,
                        u.username,
                        u.password_hash,
                        u.is_active,
                        u.failed_attempts,
                        u.locked_until,
                        r.name AS role_name,
                        l.id AS location_id,
                        l.name AS location_name
                    FROM users u
                    JOIN roles r ON u.role_id = r.id
                    LEFT JOIN locations l ON u.location_id = l.id
                    WHERE u.location_id = ?
                    ORDER BY u.full_name
                    """,
                    (location_id,),
                ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_user_counts_by_role(self) -> list[dict]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT r.name AS role_name, COUNT(u.id) AS user_count
                FROM roles r
                LEFT JOIN users u ON u.role_id = r.id
                GROUP BY r.id
                ORDER BY r.name
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_user_counts_by_location(self) -> list[dict]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT l.name AS location_name, COUNT(u.id) AS user_count
                FROM locations l
                LEFT JOIN users u ON u.location_id = l.id
                GROUP BY l.id
                ORDER BY l.name
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def create(
        self,
        full_name: str,
        username: str,
        password_hash: str,
        role_id: int,
        location_id: int | None,
        is_active: bool,
    ) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO users (
                    full_name,
                    username,
                    password_hash,
                    role_id,
                    location_id,
                    is_active
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    full_name,
                    username,
                    password_hash,
                    role_id,
                    location_id,
                    int(is_active),
                ),
            )
            connection.commit()

    def set_active(self, user_id: int, is_active: bool) -> None:
        with get_connection() as connection:
            connection.execute(
                "UPDATE users SET is_active = ? WHERE id = ?",
                (int(is_active), user_id),
            )
            connection.commit()

    def get_by_id(self, user_id: int) -> Optional[dict]:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    u.id,
                    u.full_name,
                    u.username,
                    u.password_hash,
                    u.is_active,
                    u.failed_attempts,
                    u.locked_until,
                    u.role_id,
                    u.location_id,
                    r.name AS role_name,
                    l.name AS location_name
                FROM users u
                JOIN roles r ON u.role_id = r.id
                LEFT JOIN locations l ON u.location_id = l.id
                WHERE u.id = ?
                """,
                (user_id,),
            ).fetchone()

        return self._row_to_dict(row) if row else None

    def increment_failed_attempts(self, user_id: int) -> None:
        with get_connection() as connection:
            connection.execute(
                "UPDATE users SET failed_attempts = COALESCE(failed_attempts,0) + 1 WHERE id = ?",
                (user_id,),
            )
            connection.commit()

    def reset_failed_attempts(self, user_id: int) -> None:
        with get_connection() as connection:
            connection.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
                (user_id,),
            )
            connection.commit()

    def set_locked_until(self, user_id: int, locked_until: str | None) -> None:
        with get_connection() as connection:
            connection.execute(
                "UPDATE users SET locked_until = ? WHERE id = ?",
                (locked_until, user_id),
            )
            connection.commit()

    def update_user(
        self,
        user_id: int,
        full_name: str,
        username: str,
        role_id: int,
        location_id: int | None,
        is_active: bool,
        password_hash: str | None = None,
    ) -> bool:
        with get_connection() as connection:
            if password_hash is not None:
                cursor = connection.execute(
                    """
                    UPDATE users
                    SET full_name = ?, username = ?, role_id = ?, location_id = ?, is_active = ?, password_hash = ?
                    WHERE id = ?
                    """,
                    (
                        full_name.strip(),
                        username.strip(),
                        role_id,
                        location_id,
                        int(is_active),
                        password_hash,
                        user_id,
                    ),
                )
            else:
                cursor = connection.execute(
                    """
                    UPDATE users
                    SET full_name = ?, username = ?, role_id = ?, location_id = ?, is_active = ?
                    WHERE id = ?
                    """,
                    (
                        full_name.strip(),
                        username.strip(),
                        role_id,
                        location_id,
                        int(is_active),
                        user_id,
                    ),
                )
            connection.commit()
            return cursor.rowcount > 0

    def log_audit(self, user_id: int | None, action: str, object_type: str, object_id: int | None, details: str | None = None) -> None:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO audit_logs (user_id, action, object_type, object_id, details) VALUES (?, ?, ?, ?, ?)",
                (user_id, action, object_type, object_id, details),
            )
            connection.commit()

    def _row_to_dict(self, row: Row) -> dict:
        return {
            "id": row["id"],
            "full_name": row["full_name"],
            "username": row["username"],
            "password_hash": row["password_hash"],
            "is_active": bool(row["is_active"]),
            "failed_attempts": row["failed_attempts"],
            "locked_until": row["locked_until"],
            "role_name": row["role_name"],
            "location_id": row["location_id"],
            "location_name": row["location_name"],
        }
