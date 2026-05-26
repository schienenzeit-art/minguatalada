from __future__ import annotations

import json
from typing import List

from database.db import get_connection


class FilterPresetRepository:
    def create_preset(self, user_id: int | None, name: str, filter_dict: dict) -> int | None:
        try:
            with get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO filter_presets (user_id, name, filter_json) VALUES (?, ?, ?)",
                    (user_id, name, json.dumps(filter_dict, ensure_ascii=False)),
                )
                conn.commit()
                return cursor.lastrowid
        except Exception:
            return None

    def get_presets(self, user_id: int | None) -> List[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, user_id, name, filter_json, created_at FROM filter_presets WHERE user_id = ? ORDER BY name ASC",
                (user_id,),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["filter"] = json.loads(d["filter_json"])
            except Exception:
                d["filter"] = {}
            result.append(d)
        return result

    def delete_preset(self, preset_id: int) -> bool:
        with get_connection() as conn:
            conn.execute("DELETE FROM filter_presets WHERE id = ?", (preset_id,))
            conn.commit()
        return True
