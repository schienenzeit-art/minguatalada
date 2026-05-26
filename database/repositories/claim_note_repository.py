from __future__ import annotations

from typing import List

from database.db import get_connection


class ClaimNoteRepository:
    def add_note(self, claim_id: int, user_id: int | None, note_text: str) -> int | None:
        try:
            with get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO claim_notes (claim_id, user_id, note_text) VALUES (?, ?, ?)",
                    (claim_id, user_id, note_text),
                )
                conn.commit()
                return cursor.lastrowid
        except Exception:
            return None

    def get_notes(self, claim_id: int) -> List[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT n.id, n.claim_id, n.note_text, n.created_at,
                       u.full_name AS author_name
                FROM claim_notes n
                LEFT JOIN users u ON n.user_id = u.id
                WHERE n.claim_id = ?
                ORDER BY n.created_at ASC
                """,
                (claim_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_note(self, note_id: int) -> bool:
        with get_connection() as conn:
            conn.execute("DELETE FROM claim_notes WHERE id = ?", (note_id,))
            conn.commit()
        return True
