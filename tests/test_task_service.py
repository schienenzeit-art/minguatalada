import unittest
from unittest.mock import MagicMock, patch, ANY

from services.task_service import TaskService
from core.task_status import TaskStatus
from core.task_priority import TaskPriority


class TaskServiceTest(unittest.TestCase):
    def setUp(self):
        self.task_repository = MagicMock()
        self.claim_service = MagicMock()
        self.user_service = MagicMock()
        self.location_service = MagicMock()
        self.service = TaskService(
            task_repository=self.task_repository,
            claim_service=self.claim_service,
            user_service=self.user_service,
            location_service=self.location_service,
        )

    @patch("core.session.Session.get_user_id", return_value=1)
    @patch("core.session.Session.is_admin", return_value=False)
    def test_create_task_records_audit_log(self, is_admin_mock, get_user_id_mock):
        task = {
            "id": 10,
            "title": "Rückruf bearbeiten",
            "status": TaskStatus.OFFEN,
            "priority": TaskPriority.MITTEL,
            "assigned_user_id": None,
            "location_id": None,
            "source_type": "manual",
        }
        self.task_repository.create_task.return_value = task
        self.service._record_audit_log = MagicMock()

        result = self.service.create_task(
            title="Rückruf",
            description="Kunde zurückrufen",
            task_type="Allgemein",
            status=TaskStatus.OFFEN,
            priority=TaskPriority.MITTEL,
            due_date=None,
            assigned_user_id=None,
            location_id=None,
            source_type=None,
            source_ref_type=None,
            source_ref_id=None,
            source_description=None,
        )

        self.assertEqual(result, task)
        self.assertEqual(self.service._record_audit_log.call_count, 1)
        self.assertEqual(self.service._record_audit_log.call_args.kwargs["action"], "create_task")
        self.assertEqual(self.service._record_audit_log.call_args.kwargs["object_type"], "task")
        self.assertEqual(self.service._record_audit_log.call_args.kwargs["object_id"], 10)

    @patch("core.session.Session.get_user_id", return_value=2)
    @patch("core.session.Session.is_admin", return_value=False)
    def test_update_task_permitted_for_assigned_user(self, is_admin_mock, get_user_id_mock):
        task = {"id": 5, "is_system_task": False, "assigned_user_id": 2, "created_by": 1}
        self.task_repository.get_task_by_id.return_value = task
        self.task_repository.update_task.return_value = True
        self.service._record_audit_log = MagicMock()

        result = self.service.update_task(
            task_id=5,
            title="Neue Aufgabe",
            description="Beschreibung",
            task_type="Prüfung",
            status=TaskStatus.IN_BEARBEITUNG,
            priority=TaskPriority.HOCH,
            due_date=None,
            assigned_user_id=2,
            location_id=None,
            source_type=None,
            source_ref_type=None,
            source_ref_id=None,
            source_description=None,
        )

        self.assertTrue(result)
        self.assertEqual(self.service._record_audit_log.call_count, 1)
        self.assertEqual(self.service._record_audit_log.call_args.kwargs["action"], "update_task")
        self.assertEqual(self.service._record_audit_log.call_args.kwargs["object_type"], "task")
        self.assertEqual(self.service._record_audit_log.call_args.kwargs["object_id"], 5)

    @patch("core.session.Session.get_user_id", return_value=3)
    @patch("core.session.Session.is_admin", return_value=False)
    def test_update_task_denied_for_other_user(self, is_admin_mock, get_user_id_mock):
        task = {"id": 5, "is_system_task": False, "assigned_user_id": 2, "created_by": 1}
        self.task_repository.get_task_by_id.return_value = task

        result = self.service.update_task(
            task_id=5,
            title="Neue Aufgabe",
            description="Beschreibung",
            task_type="Prüfung",
            status=TaskStatus.IN_BEARBEITUNG,
            priority=TaskPriority.HOCH,
            due_date=None,
            assigned_user_id=2,
            location_id=None,
            source_type=None,
            source_ref_type=None,
            source_ref_id=None,
            source_description=None,
        )

        self.assertFalse(result)
        self.task_repository.update_task.assert_not_called()

    @patch("core.session.Session.get_user_id", return_value=2)
    @patch("core.session.Session.is_admin", return_value=False)
    def test_mark_task_completed_permitted_for_assigned_user(self, is_admin_mock, get_user_id_mock):
        task = {"id": 7, "is_system_task": False, "assigned_user_id": 2, "created_by": 1}
        self.task_repository.get_task_by_id.return_value = task
        self.task_repository.mark_task_completed.return_value = True
        self.service._record_audit_log = MagicMock()

        result = self.service.mark_task_completed(7)

        self.assertTrue(result)
        self.assertEqual(self.service._record_audit_log.call_count, 1)
        self.assertEqual(self.service._record_audit_log.call_args.kwargs["action"], "complete_task")
        self.assertEqual(self.service._record_audit_log.call_args.kwargs["object_type"], "task")
        self.assertEqual(self.service._record_audit_log.call_args.kwargs["object_id"], 7)

    @patch("core.session.Session.get_user_id", return_value=4)
    @patch("core.session.Session.is_admin", return_value=False)
    def test_mark_task_completed_denied_for_other_user(self, is_admin_mock, get_user_id_mock):
        task = {"id": 7, "is_system_task": False, "assigned_user_id": 2, "created_by": 1}
        self.task_repository.get_task_by_id.return_value = task

        result = self.service.mark_task_completed(7)

        self.assertFalse(result)
        self.task_repository.mark_task_completed.assert_not_called()


if __name__ == "__main__":
    unittest.main()
