from typing import Dict, List

from database.db import get_connection


class ExpenseRepository:
    def save_expenses(self, claim_id: int, expenses: Dict[str, dict]) -> None:
        with get_connection() as connection:
            connection.execute("DELETE FROM expenses WHERE claim_id = ?", (claim_id,))
            for typ, data in expenses.items():
                amount = float(data.get("amount") or 0.0)
                has_proof = 1 if data.get("has_proof") else 0
                note = data.get("note")
                connection.execute(
                    "INSERT INTO expenses (claim_id, type, amount, has_proof, note) VALUES (?, ?, ?, ?, ?)",
                    (claim_id, typ, amount, has_proof, note),
                )
            connection.commit()

    def get_expenses(self, claim_id: int) -> List[Dict[str, object]]:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT type, amount, has_proof, note FROM expenses WHERE claim_id = ? ORDER BY id",
                (claim_id,),
            ).fetchall()

        return [dict(row) for row in rows]
