from typing import Dict, List

from database.db import get_connection


class IncomeRepository:
    def save_incomes(self, claim_id: int, incomes: Dict[str, float]) -> None:
        with get_connection() as connection:
            # remove existing incomes for claim
            connection.execute("DELETE FROM incomes WHERE claim_id = ?", (claim_id,))
            for typ, amount in incomes.items():
                connection.execute(
                    "INSERT INTO incomes (claim_id, type, amount) VALUES (?, ?, ?)",
                    (claim_id, typ, float(amount or 0.0)),
                )
            connection.commit()

    def get_incomes(self, claim_id: int) -> List[Dict[str, object]]:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT type, amount FROM incomes WHERE claim_id = ? ORDER BY id",
                (claim_id,),
            ).fetchall()

        return [dict(row) for row in rows]
