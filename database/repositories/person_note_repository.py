from database.db import get_connection


class PersonNoteRepository:
    def list_for_person(self, person_id: int) -> list[dict]:
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(
                """SELECT n.*, u.full_name AS author_name
                   FROM person_notes n
                   LEFT JOIN users u ON n.user_id = u.id
                   WHERE n.person_id = ?
                   ORDER BY n.created_at DESC""",
                (person_id,),
            ).fetchall()]

    def create(self, person_id: int, user_id: int | None, note_text: str) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO person_notes (person_id, user_id, note_text) VALUES (?,?,?)",
                (person_id, user_id, note_text),
            )
            conn.commit()
            return cur.lastrowid

    def delete(self, note_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM person_notes WHERE id=?", (note_id,))
            conn.commit()

    def update(self, note_id: int, note_text: str) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE person_notes SET note_text=? WHERE id=?",
                (note_text, note_id),
            )
            conn.commit()
