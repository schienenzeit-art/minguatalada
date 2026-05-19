import json
import sqlite3
from sqlite3 import Row
from typing import Any, Dict, List, Optional

from database.db import get_connection


class SettingRepository:
    def get_setting(self, key: str) -> Optional[Dict[str, Any]]:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM settings WHERE key = ?",
                (key,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def get_all_settings(self) -> List[Dict[str, Any]]:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM settings ORDER BY category, key"
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def create_setting(
        self,
        key: str,
        value: Any,
        value_type: str,
        category: str | None = None,
        description: str | None = None,
        editable_by_admin: bool = True,
        updated_by: int | None = None,
    ) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO settings (
                    key,
                    value,
                    value_type,
                    category,
                    description,
                    editable_by_admin,
                    updated_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    self._convert_value_to_text(value, value_type),
                    value_type,
                    category,
                    description,
                    int(editable_by_admin),
                    updated_by,
                ),
            )
            connection.commit()

    def update_setting_value(
        self,
        key: str,
        value: Any,
        updated_by: int | None = None,
    ) -> bool:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE settings
                SET value = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ?
                WHERE key = ?
                """,
                (
                    self._convert_value_to_text(value, self._get_value_type(connection, key)),
                    updated_by,
                    key,
                ),
            )
            connection.commit()
            return cursor.rowcount > 0

    def _get_value_type(self, connection: "sqlite3.Connection", key: str) -> str:
        row = connection.execute(
            "SELECT value_type FROM settings WHERE key = ?",
            (key,),
        ).fetchone()
        return row[0] if row else "string"

    def _row_to_dict(self, row: Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "key": row["key"],
            "value": self._parse_value(row["value"], row["value_type"]),
            "value_type": row["value_type"],
            "category": row["category"],
            "description": row["description"],
            "editable_by_admin": bool(row["editable_by_admin"]),
            "updated_by": row["updated_by"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _parse_value(self, raw_value: Any, value_type: str) -> Any:
        if raw_value is None:
            return None
        if value_type == "number":
            try:
                return float(raw_value)
            except (TypeError, ValueError):
                return 0.0
        if value_type == "boolean":
            return str(raw_value) in ("1", "true", "True")
        if value_type == "json":
            try:
                return json.loads(raw_value)
            except Exception:
                return {}
        return raw_value

    def _convert_value_to_text(self, value: Any, value_type: str) -> str:
        if value_type == "number":
            return str(float(value))
        if value_type == "boolean":
            return "1" if bool(value) else "0"
        if value_type == "json":
            return json.dumps(value, ensure_ascii=False)
        return str(value)
