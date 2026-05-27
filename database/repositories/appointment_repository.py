from database.db import get_connection


class AppointmentRepository:
    def create(self, data: dict) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO appointments
                   (person_id, claim_id, user_id, location_id, title,
                    appointment_date, appointment_time, duration_minutes, note, status, created_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    data.get("person_id"),
                    data.get("claim_id"),
                    data.get("user_id"),
                    data.get("location_id"),
                    data["title"],
                    data["appointment_date"],
                    data.get("appointment_time"),
                    data.get("duration_minutes", 30),
                    data.get("note"),
                    data.get("status", "GEPLANT"),
                    data.get("created_by"),
                ),
            )
            conn.commit()
            return cur.lastrowid

    def list_all(self, status: str | None = None, user_id: int | None = None,
                 location_id: int | None = None, from_date: str | None = None,
                 to_date: str | None = None) -> list[dict]:
        with get_connection() as conn:
            sql = """
                SELECT a.*,
                       p.first_name || ' ' || p.last_name AS person_name,
                       u.full_name AS user_name,
                       l.name AS location_name
                FROM appointments a
                LEFT JOIN persons p ON a.person_id = p.id
                LEFT JOIN users u ON a.user_id = u.id
                LEFT JOIN locations l ON a.location_id = l.id
                WHERE 1=1
            """
            params: list = []
            if status:
                sql += " AND a.status = ?"
                params.append(status)
            if user_id:
                sql += " AND a.user_id = ?"
                params.append(user_id)
            if location_id:
                sql += " AND a.location_id = ?"
                params.append(location_id)
            if from_date:
                sql += " AND a.appointment_date >= ?"
                params.append(from_date)
            if to_date:
                sql += " AND a.appointment_date <= ?"
                params.append(to_date)
            sql += " ORDER BY a.appointment_date ASC, a.appointment_time ASC"
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def get_by_id(self, appointment_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                """SELECT a.*,
                          p.first_name || ' ' || p.last_name AS person_name,
                          u.full_name AS user_name,
                          l.name AS location_name
                   FROM appointments a
                   LEFT JOIN persons p ON a.person_id = p.id
                   LEFT JOIN users u ON a.user_id = u.id
                   LEFT JOIN locations l ON a.location_id = l.id
                   WHERE a.id = ?""",
                (appointment_id,),
            ).fetchone()
            return dict(row) if row else None

    def update(self, appointment_id: int, data: dict) -> None:
        with get_connection() as conn:
            conn.execute(
                """UPDATE appointments SET
                   title=?, appointment_date=?, appointment_time=?,
                   duration_minutes=?, note=?, status=?,
                   person_id=?, claim_id=?, user_id=?, location_id=?,
                   updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (
                    data["title"],
                    data["appointment_date"],
                    data.get("appointment_time"),
                    data.get("duration_minutes", 30),
                    data.get("note"),
                    data.get("status", "GEPLANT"),
                    data.get("person_id"),
                    data.get("claim_id"),
                    data.get("user_id"),
                    data.get("location_id"),
                    appointment_id,
                ),
            )
            conn.commit()

    def delete(self, appointment_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM appointments WHERE id=?", (appointment_id,))
            conn.commit()

    def list_for_person(self, person_id: int) -> list[dict]:
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM appointments WHERE person_id=? ORDER BY appointment_date DESC",
                (person_id,),
            ).fetchall()]

    def list_upcoming(self, days: int = 7) -> list[dict]:
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(
                """SELECT a.*,
                          p.first_name || ' ' || p.last_name AS person_name,
                          u.full_name AS user_name
                   FROM appointments a
                   LEFT JOIN persons p ON a.person_id = p.id
                   LEFT JOIN users u ON a.user_id = u.id
                   WHERE a.appointment_date BETWEEN date('now') AND date('now', ? || ' days')
                     AND a.status NOT IN ('ABGESAGT','ABGESCHLOSSEN')
                   ORDER BY a.appointment_date, a.appointment_time""",
                (f"+{days}",),
            ).fetchall()]

    def count_today(self) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM appointments WHERE appointment_date=date('now') AND status='GEPLANT'"
            ).fetchone()
            return int(row["n"]) if row else 0
