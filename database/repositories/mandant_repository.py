from database.db import get_connection


class MandantRepository:
    def list_mandants(self, active_only: bool = False) -> list[dict]:
        with get_connection() as conn:
            sql = "SELECT * FROM mandants"
            if active_only:
                sql += " WHERE is_active = 1"
            sql += " ORDER BY name"
            return [dict(r) for r in conn.execute(sql).fetchall()]

    def get_by_id(self, mandant_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM mandants WHERE id = ?", (mandant_id,)).fetchone()
            return dict(row) if row else None

    def create(self, name: str, short_name: str = "", contact_email: str = "",
               contact_phone: str = "", address: str = "") -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO mandants (name, short_name, contact_email, contact_phone, address) VALUES (?,?,?,?,?)",
                (name, short_name, contact_email, contact_phone, address),
            )
            conn.commit()
            return cur.lastrowid

    def update(self, mandant_id: int, data: dict) -> None:
        with get_connection() as conn:
            conn.execute(
                """UPDATE mandants SET name=?, short_name=?, contact_email=?,
                   contact_phone=?, address=?, is_active=? WHERE id=?""",
                (data.get("name"), data.get("short_name"), data.get("contact_email"),
                 data.get("contact_phone"), data.get("address"),
                 1 if data.get("is_active", True) else 0, mandant_id),
            )
            conn.commit()

    def set_active(self, mandant_id: int, is_active: bool) -> None:
        with get_connection() as conn:
            conn.execute("UPDATE mandants SET is_active=? WHERE id=?", (1 if is_active else 0, mandant_id))
            conn.commit()
