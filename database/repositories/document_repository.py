from typing import Dict, List, Optional

from database.db import get_connection


class DocumentRepository:
    def create_document(
        self,
        title: str,
        original_file_name: str,
        file_name: str,
        storage_path: str,
        mime_type: str,
        file_size: int,
        document_type_id: int,
        status: str,
        description: str | None,
        claim_id: int | None,
        person_id: int | None,
        card_id: int | None,
        location_id: int | None,
        uploaded_by: int,
        uploaded_at: str,
        updated_at: str,
        expiry_date: str | None = None,
    ) -> int:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO documents (
                    title,
                    original_file_name,
                    file_name,
                    storage_path,
                    mime_type,
                    file_size,
                    document_type_id,
                    status,
                    description,
                    claim_id,
                    person_id,
                    card_id,
                    location_id,
                    uploaded_by,
                    uploaded_at,
                    updated_at,
                    expiry_date,
                    is_deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    title,
                    original_file_name,
                    file_name,
                    storage_path,
                    mime_type,
                    file_size,
                    document_type_id,
                    status,
                    description,
                    claim_id,
                    person_id,
                    card_id,
                    location_id,
                    uploaded_by,
                    uploaded_at,
                    updated_at,
                    expiry_date,
                ),
            )
            connection.commit()
            return cursor.lastrowid

    def get_document_by_id(self, document_id: int) -> Optional[Dict[str, object]]:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT d.*, dt.name AS document_type_name, u.full_name AS uploaded_by_name,
                       l.name AS location_name,
                       c.case_number AS claim_case_number,
                       p.first_name || ' ' || p.last_name AS person_name,
                       cards.card_number AS card_number
                FROM documents d
                LEFT JOIN document_types dt ON d.document_type_id = dt.id
                LEFT JOIN users u ON d.uploaded_by = u.id
                LEFT JOIN locations l ON d.location_id = l.id
                LEFT JOIN claims c ON d.claim_id = c.id
                LEFT JOIN persons p ON d.person_id = p.id
                LEFT JOIN cards cards ON d.card_id = cards.id
                WHERE d.id = ? AND d.is_deleted = 0
                """,
                (document_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_document_title(self, document_id: int, title: str) -> bool:
        with get_connection() as connection:
            cursor = connection.execute(
                "UPDATE documents SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title.strip(), document_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def update_document_status(self, document_id: int, status: str) -> bool:
        """Update document status (e.g., to ARCHIVIERT)."""
        with get_connection() as connection:
            archived_at = None
            if status == "ARCHIVIERT":
                from datetime import datetime
                archived_at = datetime.utcnow().isoformat()
            
            cursor = connection.execute(
                "UPDATE documents SET status = ?, archived_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, archived_at, document_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def list_documents(
        self,
        search_text: str | None = None,
        document_type_id: int | None = None,
        status: str | None = None,
        claim_id: int | None = None,
        person_id: int | None = None,
        card_id: int | None = None,
        location_id: int | None = None,
        uploaded_from: str | None = None,
        uploaded_to: str | None = None,
        uploaded_by: int | None = None,
        document_id: int | None = None,
    ) -> List[Dict[str, object]]:
        sql = [
            "SELECT d.*, dt.name AS document_type_name, u.full_name AS uploaded_by_name,",
            "       l.name AS location_name,",
            "       c.case_number AS claim_case_number,",
            "       p.first_name || ' ' || p.last_name AS person_name,",
            "       cards.card_number AS card_number",
            "FROM documents d",
            "LEFT JOIN document_types dt ON d.document_type_id = dt.id",
            "LEFT JOIN users u ON d.uploaded_by = u.id",
            "LEFT JOIN locations l ON d.location_id = l.id",
            "LEFT JOIN claims c ON d.claim_id = c.id",
            "LEFT JOIN persons p ON d.person_id = p.id",
            "LEFT JOIN cards cards ON d.card_id = cards.id",
            "WHERE d.is_deleted = 0",
        ]
        params: list[object] = []

        if document_id is not None:
            sql.append("AND d.id = ?")
            params.append(document_id)

        if document_type_id is not None:
            sql.append("AND d.document_type_id = ?")
            params.append(document_type_id)

        if status is not None:
            sql.append("AND d.status = ?")
            params.append(status)

        if claim_id is not None:
            sql.append("AND d.claim_id = ?")
            params.append(claim_id)

        if person_id is not None:
            sql.append("AND d.person_id = ?")
            params.append(person_id)

        if card_id is not None:
            sql.append("AND d.card_id = ?")
            params.append(card_id)

        if location_id is not None:
            sql.append("AND d.location_id = ?")
            params.append(location_id)

        if uploaded_by is not None:
            sql.append("AND d.uploaded_by = ?")
            params.append(uploaded_by)

        if uploaded_from is not None:
            sql.append("AND d.uploaded_at >= ?")
            params.append(uploaded_from)

        if uploaded_to is not None:
            sql.append("AND d.uploaded_at <= ?")
            params.append(uploaded_to)

        if search_text:
            search_value = f"%{search_text.lower()}%"
            sql.append(
                "AND (LOWER(d.title) LIKE ? OR LOWER(d.original_file_name) LIKE ? "
                "OR LOWER(d.description) LIKE ? OR LOWER(c.case_number) LIKE ? "
                "OR LOWER(p.first_name || ' ' || p.last_name) LIKE ? "
                "OR LOWER(cards.card_number) LIKE ? OR LOWER(l.name) LIKE ? "
                "OR LOWER(dt.name) LIKE ?)",
            )
            params.extend([search_value] * 8)

        sql.append("ORDER BY d.uploaded_at DESC")
        query = "\n".join(sql)

        with get_connection() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()

        return [dict(row) for row in rows]

    def delete_document(self, document_id: int) -> bool:
        with get_connection() as connection:
            cursor = connection.execute(
                "UPDATE documents SET is_deleted = 1 WHERE id = ?",
                (document_id,),
            )
            connection.commit()
            return cursor.rowcount > 0
