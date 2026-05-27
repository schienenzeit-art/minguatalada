from database.db import get_connection
from database.repositories.archive_repository import ArchiveRepository


class ArchiveService:
    def __init__(self, repo: ArchiveRepository | None = None):
        self.repo = repo or ArchiveRepository()

    def list_rules(self) -> list[dict]:
        return self.repo.list_rules()

    def get_rule(self, rule_id: int) -> dict | None:
        return self.repo.get_rule(rule_id)

    def update_rule(self, rule_id: int, data: dict) -> None:
        if data.get("retention_days", 0) < 1:
            raise ValueError("Aufbewahrungsdauer muss mindestens 1 Tag betragen.")
        if data.get("action") not in ("ARCHIVE", "DELETE"):
            raise ValueError("Aktion muss 'ARCHIVE' oder 'DELETE' sein.")
        self.repo.update_rule(rule_id, data)

    def count_affected(self, rule_id: int) -> int:
        rule = self.repo.get_rule(rule_id)
        if not rule:
            return 0
        return self.repo.count_affected(rule["entity_type"], rule["retention_days"])

    def run_rule(self, rule_id: int) -> int:
        """Apply a single archive rule and return the number of affected rows."""
        rule = self.repo.get_rule(rule_id)
        if not rule or not rule.get("is_active"):
            return 0

        entity_type    = rule["entity_type"]
        retention_days = rule["retention_days"]
        action         = rule["action"]

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
        count = 0

        with get_connection() as conn:
            if action == "DELETE":
                cur = conn.execute(
                    f"DELETE FROM {table} WHERE {ts_col} < datetime('now', ? || ' days')",
                    (f"-{retention_days}",),
                )
                count = cur.rowcount
            elif action == "ARCHIVE":
                # For documents: set is_deleted=1; for others: mark as archived via a flag if available
                if table == "documents":
                    cur = conn.execute(
                        f"UPDATE {table} SET is_deleted=1, archived_at=CURRENT_TIMESTAMP "
                        f"WHERE {ts_col} < datetime('now', ? || ' days') AND is_deleted=0",
                        (f"-{retention_days}",),
                    )
                    count = cur.rowcount
                else:
                    # No generic archive flag — report count only
                    row = conn.execute(
                        f"SELECT COUNT(*) AS n FROM {table} WHERE {ts_col} < datetime('now', ? || ' days')",
                        (f"-{retention_days}",),
                    ).fetchone()
                    count = int(row["n"]) if row else 0
            conn.commit()

        self.repo.mark_last_run(rule_id)
        return count

    def run_all_rules(self) -> dict[str, int]:
        results = {}
        for rule in self.repo.list_rules():
            if rule.get("is_active"):
                results[rule["entity_type"]] = self.run_rule(rule["id"])
        return results
