from sqlite3 import Row
from typing import List, Optional, Dict

from database.db import get_connection


class TaskRepository:
    def create_task(
        self,
        title: str,
        description: str,
        task_type: str,
        status: str,
        priority: str,
        due_date: str | None,
        assigned_user_id: int | None,
        location_id: int | None,
        source_type: str | None = None,
        source_ref_type: str | None = None,
        source_ref_id: int | None = None,
        source_description: str | None = None,
        is_system_task: bool = False,
        created_by: int | None = None,
    ) -> Optional[Dict[str, object]]:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tasks (
                    title,
                    description,
                    task_type,
                    status,
                    priority,
                    due_date,
                    assigned_user_id,
                    location_id,
                    source_type,
                    source_ref_type,
                    source_ref_id,
                    source_description,
                    is_system_task,
                    created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    description,
                    task_type,
                    status,
                    priority,
                    due_date,
                    assigned_user_id,
                    location_id,
                    source_type,
                    source_ref_type,
                    source_ref_id,
                    source_description,
                    1 if is_system_task else 0,
                    created_by,
                ),
            )
            connection.commit()
            task_id = cursor.lastrowid

        return self.get_task_by_id(task_id)

    def update_task(
        self,
        task_id: int,
        title: str,
        description: str,
        task_type: str,
        status: str,
        priority: str,
        due_date: str | None,
        assigned_user_id: int | None,
        location_id: int | None,
        source_type: str | None = None,
        source_ref_type: str | None = None,
        source_ref_id: int | None = None,
        source_description: str | None = None,
    ) -> bool:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks SET
                    title = ?,
                    description = ?,
                    task_type = ?,
                    status = ?,
                    priority = ?,
                    due_date = ?,
                    assigned_user_id = ?,
                    location_id = ?,
                    source_type = ?,
                    source_ref_type = ?,
                    source_ref_id = ?,
                    source_description = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    title,
                    description,
                    task_type,
                    status,
                    priority,
                    due_date,
                    assigned_user_id,
                    location_id,
                    source_type,
                    source_ref_type,
                    source_ref_id,
                    source_description,
                    task_id,
                ),
            )
            connection.commit()
        return cursor.rowcount > 0

    def get_task_by_id(self, task_id: int) -> Optional[Dict[str, object]]:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    t.*,
                    u.full_name AS assigned_user_name,
                    l.name AS location_name
                FROM tasks t
                LEFT JOIN users u ON t.assigned_user_id = u.id
                LEFT JOIN locations l ON t.location_id = l.id
                WHERE t.id = ?
                """,
                (task_id,),
            ).fetchone()

        return self._row_to_dict(row) if row else None

    def list_tasks(
        self,
        status: str | None = None,
        statuses: List[str] | None = None,
        priority: str | None = None,
        task_type: str | None = None,
        source_type: str | None = None,
        assigned_user_id: int | None = None,
        location_id: int | None = None,
        search_text: str | None = None,
        due_date_scope: str | None = None,
        include_system_tasks: bool = False,
    ) -> List[Dict[str, object]]:
        query = [
            "SELECT",
            "    t.*,",
            "    u.full_name AS assigned_user_name,",
            "    l.name AS location_name",
            "FROM tasks t",
            "LEFT JOIN users u ON t.assigned_user_id = u.id",
            "LEFT JOIN locations l ON t.location_id = l.id",
            "WHERE 1=1",
        ]
        params: list[object] = []

        if not include_system_tasks:
            query.append("AND t.is_system_task = 0")

        if status is not None:
            query.append("AND t.status = ?")
            params.append(status)

        if statuses is not None:
            placeholders = ",".join(["?" for _ in statuses])
            query.append(f"AND t.status IN ({placeholders})")
            params.extend(statuses)

        if priority is not None:
            query.append("AND t.priority = ?")
            params.append(priority)

        if task_type is not None:
            query.append("AND t.task_type = ?")
            params.append(task_type)

        if assigned_user_id is not None:
            query.append("AND t.assigned_user_id = ?")
            params.append(assigned_user_id)

        if location_id is not None:
            query.append("AND t.location_id = ?")
            params.append(location_id)

        if source_type is not None:
            query.append("AND t.source_type = ?")
            params.append(source_type)

        if due_date_scope == "today":
            query.append("AND DATE(t.due_date) = DATE('now')")
        elif due_date_scope == "overdue":
            query.append("AND t.due_date IS NOT NULL AND DATE(t.due_date) < DATE('now') AND t.status != ?")
            params.append("ERLEDIGT")

        if search_text:
            query.append(
                "AND (LOWER(t.title) LIKE ? OR LOWER(t.description) LIKE ? OR LOWER(t.source_description) LIKE ?)",
            )
            search_pattern = f"%{search_text.strip().lower()}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        query.append("ORDER BY CASE WHEN t.status = 'ERLEDIGT' THEN 1 ELSE 0 END, DATE(t.due_date) ASC")
        sql = " ".join(query)

        with get_connection() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def mark_task_completed(self, task_id: int) -> bool:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks SET
                    status = ?,
                    completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                ("ERLEDIGT", task_id),
            )
            connection.commit()
        return cursor.rowcount > 0

    def count_open_tasks(self, assigned_user_id: int | None = None, location_id: int | None = None) -> int:
        query = ["SELECT COUNT(*) AS total FROM tasks WHERE status != ? AND is_system_task = 0"]
        params: list[object] = ["ERLEDIGT"]

        if assigned_user_id is not None:
            query.append("AND assigned_user_id = ?")
            params.append(assigned_user_id)

        if location_id is not None:
            query.append("AND location_id = ?")
            params.append(location_id)

        sql = " ".join(query)

        with get_connection() as connection:
            row = connection.execute(sql, tuple(params)).fetchone()

        return int(row["total"] if row else 0)

    def _row_to_dict(self, row: Row) -> Dict[str, object]:
        item = dict(row)
        item["is_system_task"] = bool(item.get("is_system_task"))
        return item
