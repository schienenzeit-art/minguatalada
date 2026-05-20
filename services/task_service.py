import json
from datetime import date
from typing import List, Dict, Optional

from core.session import Session
from core.task_priority import TaskPriority
from core.task_status import TaskStatus
from core.task_type import TaskType
from core.task_source_type import TaskSourceType
from core.claim_status import ClaimStatus
from database.db import get_connection
from database.repositories.task_repository import TaskRepository
from services.claim_service import ClaimService
from services.location_service import LocationService
from services.user_service import UserService


class TaskService:
    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        claim_service: ClaimService | None = None,
        user_service: UserService | None = None,
        location_service: LocationService | None = None,
    ):
        self.task_repository = task_repository or TaskRepository()
        self.claim_service = claim_service or ClaimService()
        self.user_service = user_service or UserService()
        self.location_service = location_service or LocationService()

    def create_task(
        self,
        title: str,
        description: str,
        task_type: str,
        status: str,
        priority: str,
        due_date: Optional[str],
        assigned_user_id: Optional[int],
        location_id: Optional[int],
        source_type: Optional[str] = None,
        source_ref_type: Optional[str] = None,
        source_ref_id: Optional[int] = None,
        source_description: Optional[str] = None,
    ) -> Dict[str, object]:
        if not title.strip():
            raise ValueError("Titel ist erforderlich")

        if status not in TaskStatus.ALL_STATUSES:
            raise ValueError("Ungültiger Aufgabenstatus")

        if priority not in TaskPriority.ALL_PRIORITIES:
            raise ValueError("Ungültige Priorität")

        created_by = Session.get_user_id()
        task = self.task_repository.create_task(
            title=title.strip(),
            description=description.strip(),
            task_type=task_type.strip(),
            status=status,
            priority=priority,
            due_date=due_date,
            assigned_user_id=assigned_user_id,
            location_id=location_id,
            source_type=source_type or TaskSourceType.MANUAL,
            source_ref_type=source_ref_type,
            source_ref_id=source_ref_id,
            source_description=source_description,
            is_system_task=False,
            created_by=created_by,
        )

        if task and task.get("id") is not None:
            self._record_audit_log(
                action="create_task",
                object_type="task",
                object_id=task["id"],
                details={
                    "task_id": task["id"],
                    "title": task["title"],
                    "status": task["status"],
                    "priority": task["priority"],
                    "assigned_user_id": task.get("assigned_user_id"),
                    "location_id": task.get("location_id"),
                    "source_type": task.get("source_type"),
                },
            )

        return task

    def update_task(
        self,
        task_id: int,
        title: str,
        description: str,
        task_type: str,
        status: str,
        priority: str,
        due_date: Optional[str],
        assigned_user_id: Optional[int],
        location_id: Optional[int],
        source_type: Optional[str] = None,
        source_ref_type: Optional[str] = None,
        source_ref_id: Optional[int] = None,
        source_description: Optional[str] = None,
    ) -> bool:
        if not title.strip():
            raise ValueError("Titel ist erforderlich")

        if status not in TaskStatus.ALL_STATUSES:
            raise ValueError("Ungültiger Aufgabenstatus")

        if priority not in TaskPriority.ALL_PRIORITIES:
            raise ValueError("Ungültige Priorität")

        task = self.get_task(task_id)
        if task is None or not self._can_modify_task(task):
            return False

        if task.get("is_system_task"):
            return False

        updated = self.task_repository.update_task(
            task_id=task_id,
            title=title.strip(),
            description=description.strip(),
            task_type=task_type.strip(),
            status=status,
            priority=priority,
            due_date=due_date,
            assigned_user_id=assigned_user_id,
            location_id=location_id,
            source_type=source_type,
            source_ref_type=source_ref_type,
            source_ref_id=source_ref_id,
            source_description=source_description,
        )

        if updated:
            self._record_audit_log(
                action="update_task",
                object_type="task",
                object_id=task_id,
                details={
                    "task_id": task_id,
                    "before": {
                        "title": task.get("title"),
                        "status": task.get("status"),
                        "priority": task.get("priority"),
                        "assigned_user_id": task.get("assigned_user_id"),
                        "location_id": task.get("location_id"),
                    },
                    "after": {
                        "title": title.strip(),
                        "status": status,
                        "priority": priority,
                        "assigned_user_id": assigned_user_id,
                        "location_id": location_id,
                    },
                },
            )

        return updated

    def get_task(self, task_id: int) -> Optional[Dict[str, object]]:
        return self.task_repository.get_task_by_id(task_id)

    def _can_modify_task(self, task: Dict[str, object]) -> bool:
        if Session.is_admin():
            return True
        current_user_id = Session.get_user_id()
        if task.get("is_system_task"):
            return False
        return (
            task.get("assigned_user_id") == current_user_id
            or task.get("created_by") == current_user_id
        )

    def _record_audit_log(self, action: str, object_type: str, object_id: int, details: Dict[str, object]) -> None:
        payload = json.dumps(details, ensure_ascii=False)
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO audit_logs (user_id, action, object_type, object_id, details) VALUES (?, ?, ?, ?, ?)",
                (
                    Session.get_user_id(),
                    action,
                    object_type,
                    object_id,
                    payload,
                ),
            )
            connection.commit()

    def mark_task_completed(self, task_id: int) -> bool:
        task = self.get_task(task_id)
        if task is None or not self._can_modify_task(task):
            return False

        if self.task_repository.mark_task_completed(task_id):
            self._record_audit_log(
                action="complete_task",
                object_type="task",
                object_id=task_id,
                details={
                    "task_id": task_id,
                    "status": TaskStatus.ERLEDIGT,
                    "title": task.get("title"),
                },
            )
            return True

        return False

    def list_manual_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        task_type: Optional[str] = None,
        source_type: Optional[str] = None,
        assigned_user_id: Optional[int] = None,
        location_id: Optional[int] = None,
        due_date_scope: Optional[str] = None,
        search_text: Optional[str] = None,
        mine_only: bool = False,
    ) -> List[Dict[str, object]]:
        if mine_only and assigned_user_id is None:
            assigned_user_id = Session.get_user_id()

        if not Session.is_admin() and not mine_only:
            assigned_user_id = Session.get_user_id()

        return self.task_repository.list_tasks(
            status=status,
            priority=priority,
            task_type=task_type,
            source_type=source_type,
            assigned_user_id=assigned_user_id,
            location_id=location_id,
            due_date_scope=due_date_scope,
            search_text=search_text,
            include_system_tasks=False,
        )

    def list_system_tasks(
        self,
        location_id: Optional[int] = None,
        assigned_user_id: Optional[int] = None,
        mine_only: bool = False,
        search_text: Optional[str] = None,
        due_date_scope: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        current_user_id = Session.get_user_id()
        if mine_only and assigned_user_id is None:
            assigned_user_id = current_user_id

        if not Session.is_admin() and not mine_only:
            user_location_id = Session.get_location_id()
            location_id = location_id or user_location_id

        claims = self.claim_service.list_claims(
            status=ClaimStatus.IN_PRUEFUNG,
            location_id=location_id,
            search_text=search_text,
        )

        tasks = []
        for claim in claims:
            if assigned_user_id is not None and claim.get("examiner_id") != assigned_user_id:
                continue

            if due_date_scope == "today" and claim.get("start_date") != date.today().isoformat():
                continue
            if due_date_scope == "overdue" and claim.get("start_date") is not None:
                if claim.get("start_date") >= date.today().isoformat():
                    continue

            task = {
                "id": f"sys-claim-{claim['id']}",
                "title": f"Antrag prüfen: {claim.get('case_number') or claim.get('description', '')}",
                "description": claim.get("description", ""),
                "task_type": "Prüfung",
                "status": TaskStatus.OFFEN,
                "priority": TaskPriority.HOCH,
                "due_date": claim.get("start_date"),
                "assigned_user_id": claim.get("examiner_id"),
                "assigned_user_name": claim.get("examiner_name") or "Nicht zugewiesen",
                "location_id": claim.get("location_id"),
                "location_name": claim.get("location_name"),
                "source_type": "system",
                "source_ref_type": "claim",
                "source_ref_id": claim["id"],
                "source_description": "Offener Anspruch wartet auf Prüfung",
                "is_system_task": True,
                "created_by": None,
            }
            tasks.append(task)

        return tasks

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        task_type: Optional[str] = None,
        assigned_user_id: Optional[int] = None,
        location_id: Optional[int] = None,
        source_type: Optional[str] = None,
        due_date_scope: Optional[str] = None,
        mine_only: bool = False,
        search_text: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        manual_tasks: List[Dict[str, object]] = []
        system_tasks: List[Dict[str, object]] = []

        if source_type in (None, TaskSourceType.MANUAL):
            manual_tasks = self.list_manual_tasks(
                status=status,
                priority=priority,
                task_type=task_type,
                source_type=source_type,
                assigned_user_id=assigned_user_id,
                location_id=location_id,
                due_date_scope=due_date_scope,
                search_text=search_text,
                mine_only=mine_only,
            )

        if source_type in (None, TaskSourceType.SYSTEM):
            system_tasks = self.list_system_tasks(
                location_id=location_id,
                assigned_user_id=assigned_user_id,
                mine_only=mine_only,
                search_text=search_text,
                due_date_scope=due_date_scope,
            )

        tasks = manual_tasks + system_tasks
        tasks.sort(
            key=lambda item: (
                item.get("status") == TaskStatus.ERLEDIGT,
                item.get("due_date") or "9999-12-31",
                TaskPriority.ALL_PRIORITIES.index(item.get("priority"))
                if item.get("priority") in TaskPriority.ALL_PRIORITIES
                else len(TaskPriority.ALL_PRIORITIES),
            )
        )
        return tasks

    def count_open_tasks(self) -> int:
        manual_open = self.task_repository.count_open_tasks(
            assigned_user_id=None if Session.is_admin() else Session.get_user_id(),
            location_id=None if Session.is_admin() else Session.get_location_id(),
        )
        system_tasks = self.list_system_tasks(
            location_id=None if Session.is_admin() else Session.get_location_id(),
            mine_only=False,
        )
        return manual_open + len(system_tasks)
