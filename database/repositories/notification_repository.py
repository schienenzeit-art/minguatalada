from database.db import get_connection


class NotificationRepository:
    def create(self, user_id: int | None, type_: str, title: str,
               message: str = "", reference_type: str | None = None,
               reference_id: int | None = None) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO notifications (user_id, type, title, message, reference_type, reference_id)
                   VALUES (?,?,?,?,?,?)""",
                (user_id, type_, title, message, reference_type, reference_id),
            )
            conn.commit()
            return cur.lastrowid

    def list_for_user(self, user_id: int, unread_only: bool = False, limit: int = 50) -> list[dict]:
        with get_connection() as conn:
            sql = "SELECT * FROM notifications WHERE (user_id = ? OR user_id IS NULL)"
            params: list = [user_id]
            if unread_only:
                sql += " AND is_read = 0"
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def count_unread(self, user_id: int) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM notifications WHERE (user_id = ? OR user_id IS NULL) AND is_read = 0",
                (user_id,),
            ).fetchone()
            return int(row["n"]) if row else 0

    def mark_read(self, notification_id: int) -> None:
        with get_connection() as conn:
            conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
            conn.commit()

    def mark_all_read(self, user_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE notifications SET is_read = 1 WHERE user_id = ? OR user_id IS NULL",
                (user_id,),
            )
            conn.commit()

    def delete_old(self, days: int = 90) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM notifications WHERE created_at < datetime('now', ? || ' days')",
                (f"-{days}",),
            )
            conn.commit()
            return cur.rowcount
