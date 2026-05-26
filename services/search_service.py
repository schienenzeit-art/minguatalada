from __future__ import annotations

from database.db import get_connection


class SearchService:
    """Globale Volltextsuche über Personen, Fälle und Dokumente."""

    def search(self, query: str, limit: int = 20) -> dict:
        if not query or not query.strip():
            return {"persons": [], "claims": [], "documents": []}

        q = f"%{query.strip()}%"

        with get_connection() as conn:
            persons = conn.execute(
                """
                SELECT id, first_name, last_name, address, city
                FROM persons
                WHERE first_name LIKE ? OR last_name LIKE ?
                   OR (first_name || ' ' || last_name) LIKE ?
                   OR address LIKE ? OR city LIKE ?
                LIMIT ?
                """,
                (q, q, q, q, q, limit),
            ).fetchall()

            claims = conn.execute(
                """
                SELECT c.id, c.case_number, c.status, c.description,
                       p.first_name AS person_first_name, p.last_name AS person_last_name,
                       l.name AS location_name
                FROM claims c
                LEFT JOIN persons p ON c.person_id = p.id
                LEFT JOIN locations l ON c.location_id = l.id
                WHERE c.case_number LIKE ? OR c.description LIKE ?
                   OR (p.first_name || ' ' || p.last_name) LIKE ?
                LIMIT ?
                """,
                (q, q, q, limit),
            ).fetchall()

            documents = conn.execute(
                """
                SELECT d.id, d.title, d.status, d.uploaded_at,
                       dt.name AS document_type_name
                FROM documents d
                LEFT JOIN document_types dt ON d.document_type_id = dt.id
                WHERE d.is_deleted = 0
                  AND (d.title LIKE ? OR d.description LIKE ?)
                LIMIT ?
                """,
                (q, q, limit),
            ).fetchall()

        def _fmt_person(r) -> dict:
            return {
                "id": r["id"],
                "name": f"{r['first_name']} {r['last_name']}".strip(),
                "detail": f"{r['address'] or ''}, {r['city'] or ''}".strip(", "),
            }

        def _fmt_claim(r) -> dict:
            person = f"{r['person_first_name'] or ''} {r['person_last_name'] or ''}".strip()
            return {
                "id": r["id"],
                "case_number": r["case_number"],
                "status": r["status"],
                "location": r["location_name"] or "-",
                "person": person or "-",
            }

        def _fmt_doc(r) -> dict:
            return {
                "id": r["id"],
                "title": r["title"],
                "type": r["document_type_name"] or "-",
                "uploaded_at": (r["uploaded_at"] or "")[:10],
            }

        return {
            "persons": [_fmt_person(r) for r in persons],
            "claims": [_fmt_claim(r) for r in claims],
            "documents": [_fmt_doc(r) for r in documents],
        }
