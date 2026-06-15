from database.db import get_connection, IS_POSTGRES


class WiedervorlageRepository:

    def create(self, user_id: int, due_date: str, note: str | None,
               claim_id: int | None = None, person_id: int | None = None) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO wiedervorlagen
                   (user_id, due_date, note, claim_id, person_id)
                   VALUES (?,?,?,?,?)""",
                (user_id, due_date, note, claim_id, person_id),
            )
            conn.commit()
            return cur.lastrowid

    def list_for_user(self, user_id: int, only_open: bool = True) -> list[dict]:
        with get_connection() as conn:
            sql = """SELECT w.*,
                            c.case_number,
                            p.first_name || ' ' || p.last_name AS person_name
                     FROM wiedervorlagen w
                     LEFT JOIN claims c ON w.claim_id = c.id
                     LEFT JOIN persons p ON w.person_id = p.id
                     WHERE w.user_id = ?"""
            params: list = [user_id]
            if only_open:
                sql += " AND w.is_done = 0"
            sql += " ORDER BY w.due_date ASC"
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def list_due_today(self, user_id: int) -> list[dict]:
        if IS_POSTGRES:
            today_cond = "w.due_date <= CURRENT_DATE::text"
        else:
            today_cond = "DATE(w.due_date) <= DATE('now')"
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(
                f"""SELECT w.*, c.case_number,
                          p.first_name || ' ' || p.last_name AS person_name
                   FROM wiedervorlagen w
                   LEFT JOIN claims c ON w.claim_id = c.id
                   LEFT JOIN persons p ON w.person_id = p.id
                   WHERE w.user_id=? AND w.is_done=0
                     AND {today_cond}
                   ORDER BY w.due_date ASC""",
                (user_id,),
            ).fetchall()]

    def mark_done(self, wiedervorlage_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE wiedervorlagen SET is_done=1, done_at=CURRENT_TIMESTAMP WHERE id=?",
                (wiedervorlage_id,),
            )
            conn.commit()

    def delete(self, wiedervorlage_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM wiedervorlagen WHERE id=?", (wiedervorlage_id,))
            conn.commit()

    def count_due(self, user_id: int) -> int:
        if IS_POSTGRES:
            today_cond = "due_date <= CURRENT_DATE::text"
        else:
            today_cond = "DATE(due_date) <= DATE('now')"
        with get_connection() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) AS n FROM wiedervorlagen"
                f" WHERE user_id=? AND is_done=0 AND {today_cond}",
                (user_id,),
            ).fetchone()
            return int(row["n"]) if row else 0
