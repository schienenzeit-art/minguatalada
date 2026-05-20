from typing import Dict, List, Optional

from database.db import get_connection


class DocumentTypeRepository:
    def list_document_types(self, include_inactive: bool = False) -> List[Dict[str, object]]:
        with get_connection() as connection:
            if include_inactive:
                rows = connection.execute(
                    "SELECT id, name, description, is_active FROM document_types ORDER BY name"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT id, name, description, is_active FROM document_types WHERE is_active = 1 ORDER BY name"
                ).fetchall()

        return [dict(row) for row in rows]

    def get_document_type_by_id(self, document_type_id: int) -> Optional[Dict[str, object]]:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT id, name, description, is_active FROM document_types WHERE id = ?",
                (document_type_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_document_type(self, name: str, description: str = "", is_active: int = 1) -> int:
        with get_connection() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO document_types (name, description, is_active) VALUES (?, ?, ?)",
                (name.strip(), description.strip(), is_active),
            )
            connection.commit()
            if cursor.lastrowid:
                return cursor.lastrowid
            row = connection.execute(
                "SELECT id FROM document_types WHERE name = ? LIMIT 1",
                (name.strip(),),
            ).fetchone()
            return int(row[0]) if row else 0
