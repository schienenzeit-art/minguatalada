from database.db import get_connection


class ReEvaluationRepository:

    def create_request(self, claim_id: int, requested_by: int, reason: str | None) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO re_evaluation_requests
                   (claim_id, requested_by, request_reason, status)
                   VALUES (?,?,?,'PENDING')""",
                (claim_id, requested_by, reason),
            )
            conn.commit()
            return cur.lastrowid

    def get_pending_for_claim(self, claim_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                """SELECT r.*, u.full_name AS requester_name
                   FROM re_evaluation_requests r
                   LEFT JOIN users u ON r.requested_by = u.id
                   WHERE r.claim_id=? AND r.status='PENDING'
                   ORDER BY r.requested_at DESC LIMIT 1""",
                (claim_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_approved_unused_for_claim(self, claim_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM re_evaluation_requests
                   WHERE claim_id=? AND status='APPROVED' AND consumed_at IS NULL
                   ORDER BY reviewed_at DESC LIMIT 1""",
                (claim_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_pending(self) -> list[dict]:
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(
                """SELECT r.*,
                          c.case_number,
                          p.first_name || ' ' || p.last_name AS person_name,
                          u.full_name AS requester_name,
                          sup.full_name AS reviewer_name
                   FROM re_evaluation_requests r
                   JOIN claims c ON r.claim_id = c.id
                   LEFT JOIN persons p ON c.person_id = p.id
                   LEFT JOIN users u ON r.requested_by = u.id
                   LEFT JOIN users sup ON r.reviewed_by = sup.id
                   WHERE r.status = 'PENDING'
                   ORDER BY r.requested_at DESC"""
            ).fetchall()]

    def list_all(self, claim_id: int | None = None) -> list[dict]:
        with get_connection() as conn:
            sql = """SELECT r.*,
                            c.case_number,
                            p.first_name || ' ' || p.last_name AS person_name,
                            u.full_name AS requester_name,
                            sup.full_name AS reviewer_name
                     FROM re_evaluation_requests r
                     JOIN claims c ON r.claim_id = c.id
                     LEFT JOIN persons p ON c.person_id = p.id
                     LEFT JOIN users u ON r.requested_by = u.id
                     LEFT JOIN users sup ON r.reviewed_by = sup.id"""
            params: list = []
            if claim_id is not None:
                sql += " WHERE r.claim_id=?"
                params.append(claim_id)
            sql += " ORDER BY r.requested_at DESC"
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def review(self, request_id: int, reviewed_by: int, status: str, comment: str | None) -> None:
        with get_connection() as conn:
            conn.execute(
                """UPDATE re_evaluation_requests SET
                   reviewed_by=?, reviewed_at=CURRENT_TIMESTAMP,
                   status=?, review_comment=?
                   WHERE id=?""",
                (reviewed_by, status, comment, request_id),
            )
            conn.commit()

    def consume(self, request_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE re_evaluation_requests SET consumed_at=CURRENT_TIMESTAMP WHERE id=?",
                (request_id,),
            )
            conn.commit()

    def count_pending(self) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM re_evaluation_requests WHERE status='PENDING'"
            ).fetchone()
            return int(row["n"]) if row else 0

    def get_by_id(self, request_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM re_evaluation_requests WHERE id=?", (request_id,)
            ).fetchone()
            return dict(row) if row else None
