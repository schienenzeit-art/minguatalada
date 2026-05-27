from database.db import get_connection


class AuditRepository:
    def log(self, user_id: int | None, action: str, object_type: str,
            object_id: int | None = None, details: str | None = None) -> None:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO audit_logs (user_id, action, object_type, object_id, details)
                   VALUES (?,?,?,?,?)""",
                (user_id, action, object_type, object_id, details),
            )
            conn.commit()

    def list_logs(self, object_type: str | None = None, user_id: int | None = None,
                  limit: int = 200, offset: int = 0) -> list[dict]:
        with get_connection() as conn:
            sql = """
                SELECT al.*, u.full_name AS user_name
                FROM audit_logs al
                LEFT JOIN users u ON al.user_id = u.id
                WHERE 1=1
            """
            params: list = []
            if object_type:
                sql += " AND al.object_type = ?"
                params.append(object_type)
            if user_id:
                sql += " AND al.user_id = ?"
                params.append(user_id)
            sql += " ORDER BY al.timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def count(self, object_type: str | None = None, user_id: int | None = None) -> int:
        with get_connection() as conn:
            sql = "SELECT COUNT(*) AS n FROM audit_logs WHERE 1=1"
            params: list = []
            if object_type:
                sql += " AND object_type = ?"
                params.append(object_type)
            if user_id:
                sql += " AND user_id = ?"
                params.append(user_id)
            row = conn.execute(sql, params).fetchone()
            return int(row["n"]) if row else 0

    def delete_old(self, days: int = 2555) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM audit_logs WHERE timestamp < datetime('now', ? || ' days')",
                (f"-{days}",),
            )
            conn.commit()
            return cur.rowcount
