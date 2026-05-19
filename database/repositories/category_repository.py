from typing import List, Dict

from database.db import get_connection


class CategoryRepository:
    def list_categories(self) -> List[Dict[str, object]]:
        with get_connection() as connection:
            rows = connection.execute("SELECT id, name FROM categories ORDER BY name").fetchall()

        return [dict(r) for r in rows]
