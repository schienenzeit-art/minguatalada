from database.db import get_connection


class ApprovalRepository:
    def create(self, claim_id: int, requested_by: int | None) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO approval_requests (claim_id, requested_by, status)
                   VALUES (?,?,'PENDING')""",
                (claim_id, requested_by),
            )
            conn.commit()
            return cur.lastrowid

    def list_pending(self) -> list[dict]:
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(
                """SELECT ar.*,
                          c.case_number,
                          p.first_name || ' ' || p.last_name AS person_name,
                          u.full_name AS requester_name
                   FROM approval_requests ar
                   JOIN claims c ON ar.claim_id = c.id
                   LEFT JOIN persons p ON c.person_id = p.id
                   LEFT JOIN users u ON ar.requested_by = u.id
                   WHERE ar.status = 'PENDING'
                   ORDER BY ar.requested_at DESC"""
            ).fetchall()]

    def list_for_claim(self, claim_id: int) -> list[dict]:
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(
                """SELECT ar.*,
                          req.full_name AS requester_name,
                          rev.full_name AS reviewer_name
                   FROM approval_requests ar
                   LEFT JOIN users req ON ar.requested_by = req.id
                   LEFT JOIN users rev ON ar.reviewed_by = rev.id
                   WHERE ar.claim_id = ?
                   ORDER BY ar.requested_at DESC""",
                (claim_id,),
            ).fetchall()]

    def review(self, request_id: int, reviewed_by: int, status: str, comment: str | None) -> None:
        with get_connection() as conn:
            conn.execute(
                """UPDATE approval_requests SET
                   reviewed_by=?, reviewed_at=CURRENT_TIMESTAMP,
                   status=?, comment=?
                   WHERE id=?""",
                (reviewed_by, status, comment, request_id),
            )
            conn.commit()

    def get_by_id(self, request_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM approval_requests WHERE id=?", (request_id,)
            ).fetchone()
            return dict(row) if row else None

    def count_pending(self) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM approval_requests WHERE status='PENDING'"
            ).fetchone()
            return int(row["n"]) if row else 0
