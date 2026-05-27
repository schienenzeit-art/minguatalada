from database.db import get_connection


class ArchiveRepository:
    def list_rules(self) -> list[dict]:
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM archive_rules ORDER BY entity_type"
            ).fetchall()]

    def get_rule(self, rule_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM archive_rules WHERE id=?", (rule_id,)).fetchone()
            return dict(row) if row else None

    def get_by_entity(self, entity_type: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM archive_rules WHERE entity_type=?", (entity_type,)
            ).fetchone()
            return dict(row) if row else None

    def update_rule(self, rule_id: int, data: dict) -> None:
        with get_connection() as conn:
            conn.execute(
                """UPDATE archive_rules SET
                   retention_days=?, action=?, description=?, is_active=?
                   WHERE id=?""",
                (
                    data["retention_days"],
                    data["action"],
                    data.get("description"),
                    1 if data.get("is_active", True) else 0,
                    rule_id,
                ),
            )
            conn.commit()

    def mark_last_run(self, rule_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE archive_rules SET last_run_at=CURRENT_TIMESTAMP WHERE id=?",
                (rule_id,),
            )
            conn.commit()

    def count_affected(self, entity_type: str, retention_days: int) -> int:
        """Count rows that would be affected by this rule."""
        table_map = {
            "claims":     ("claims",     "created_at"),
            "persons":    ("persons",    "created_at"),
            "documents":  ("documents",  "uploaded_at"),
            "cards":      ("cards",      "created_at"),
            "audit_logs": ("audit_logs", "timestamp"),
        }
        if entity_type not in table_map:
            return 0
        table, ts_col = table_map[entity_type]
        with get_connection() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) AS n FROM {table} WHERE {ts_col} < datetime('now', ? || ' days')",
                (f"-{retention_days}",),
            ).fetchone()
            return int(row["n"]) if row else 0
