from database.db import get_connection


class DocumentTemplateRepository:
    def list_templates(self, include_inactive: bool = False) -> list[dict]:
        with get_connection() as conn:
            sql = """SELECT dt.*, c.name AS category_name
                     FROM document_templates dt
                     LEFT JOIN categories c ON dt.category_id = c.id"""
            if not include_inactive:
                sql += " WHERE dt.is_active = 1"
            sql += " ORDER BY dt.template_type, dt.name"
            return [dict(r) for r in conn.execute(sql).fetchall()]

    def get_by_id(self, template_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM document_templates WHERE id=?", (template_id,)
            ).fetchone()
            return dict(row) if row else None

    def create(self, data: dict) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO document_templates
                   (name, template_type, description, body_text, category_id, is_active, created_by)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    data["name"],
                    data.get("template_type", "BRIEF"),
                    data.get("description"),
                    data.get("body_text", ""),
                    data.get("category_id"),
                    1 if data.get("is_active", True) else 0,
                    data.get("created_by"),
                ),
            )
            conn.commit()
            return cur.lastrowid

    def update(self, template_id: int, data: dict) -> None:
        with get_connection() as conn:
            conn.execute(
                """UPDATE document_templates SET
                   name=?, template_type=?, description=?, body_text=?,
                   category_id=?, is_active=?, updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (
                    data["name"],
                    data.get("template_type", "BRIEF"),
                    data.get("description"),
                    data.get("body_text", ""),
                    data.get("category_id"),
                    1 if data.get("is_active", True) else 0,
                    template_id,
                ),
            )
            conn.commit()

    def delete(self, template_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM document_templates WHERE id=?", (template_id,))
            conn.commit()
