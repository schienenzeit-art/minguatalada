from database.db import get_connection


class ChecklistRepository:
    # ── Templates ─────────────────────────────────────────────────────────────
    def list_templates(self) -> list[dict]:
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(
                """SELECT ct.*, c.name AS category_name,
                          COUNT(ci.id) AS item_count
                   FROM checklist_templates ct
                   LEFT JOIN categories c ON ct.category_id = c.id
                   LEFT JOIN checklist_items ci ON ci.template_id = ct.id
                   GROUP BY ct.id
                   ORDER BY ct.name"""
            ).fetchall()]

    def get_template(self, template_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM checklist_templates WHERE id=?", (template_id,)
            ).fetchone()
            return dict(row) if row else None

    def create_template(self, name: str, category_id: int | None = None) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO checklist_templates (name, category_id) VALUES (?,?)",
                (name, category_id),
            )
            conn.commit()
            return cur.lastrowid

    def delete_template(self, template_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM checklist_templates WHERE id=?", (template_id,))
            conn.commit()

    def list_items_for_template(self, template_id: int) -> list[dict]:
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM checklist_items WHERE template_id=? ORDER BY sort_order, id",
                (template_id,),
            ).fetchall()]

    def add_template_item(self, template_id: int, label: str,
                          is_required: bool = True, sort_order: int = 0) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO checklist_items (template_id, label, is_required, sort_order) VALUES (?,?,?,?)",
                (template_id, label, 1 if is_required else 0, sort_order),
            )
            conn.commit()
            return cur.lastrowid

    def delete_template_item(self, item_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM checklist_items WHERE id=?", (item_id,))
            conn.commit()

    # ── Claim-Checklisten ──────────────────────────────────────────────────────
    def list_claim_items(self, claim_id: int) -> list[dict]:
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(
                """SELECT cci.*, u.full_name AS checked_by_name
                   FROM claim_checklist_items cci
                   LEFT JOIN users u ON cci.checked_by = u.id
                   WHERE cci.claim_id = ?
                   ORDER BY cci.sort_order, cci.id""",
                (claim_id,),
            ).fetchall()]

    def add_claim_item(self, claim_id: int, label: str,
                       is_required: bool = True, sort_order: int = 0) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO claim_checklist_items
                   (claim_id, label, is_required, sort_order)
                   VALUES (?,?,?,?)""",
                (claim_id, label, 1 if is_required else 0, sort_order),
            )
            conn.commit()
            return cur.lastrowid

    def set_item_checked(self, item_id: int, checked: bool, checked_by: int | None) -> None:
        with get_connection() as conn:
            if checked:
                conn.execute(
                    """UPDATE claim_checklist_items SET
                       is_checked=1, checked_by=?, checked_at=CURRENT_TIMESTAMP
                       WHERE id=?""",
                    (checked_by, item_id),
                )
            else:
                conn.execute(
                    "UPDATE claim_checklist_items SET is_checked=0, checked_by=NULL, checked_at=NULL WHERE id=?",
                    (item_id,),
                )
            conn.commit()

    def delete_claim_item(self, item_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM claim_checklist_items WHERE id=?", (item_id,))
            conn.commit()

    def apply_template_to_claim(self, claim_id: int, template_id: int) -> int:
        items = self.list_items_for_template(template_id)
        count = 0
        for item in items:
            self.add_claim_item(
                claim_id=claim_id,
                label=item["label"],
                is_required=bool(item["is_required"]),
                sort_order=item["sort_order"],
            )
            count += 1
        return count
