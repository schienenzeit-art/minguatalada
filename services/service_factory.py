"""
Lightweight factories that build fully-wired service instances without a DI container.
Used as fallbacks in UI dialogs when no pre-built service is injected via the container.
Each factory mirrors the wiring in app/container.py:build_service_container().
"""
from __future__ import annotations


def make_claim_service():
    from services.claim_service import ClaimService
    from services.settings_service import SettingsService
    from services.re_evaluation_service import ReEvaluationService
    from services.notification_service import NotificationService
    from services.audit_service import AuditService
    from database.repositories.claim_repository import ClaimRepository
    from database.repositories.income_repository import IncomeRepository
    from database.repositories.expense_repository import ExpenseRepository
    from database.repositories.re_evaluation_repository import ReEvaluationRepository
    from database.repositories.audit_repository import AuditRepository
    from database.repositories.notification_repository import NotificationRepository
    from database.repositories.claim_note_repository import ClaimNoteRepository

    audit_svc = AuditService(repo=AuditRepository())
    notification_svc = NotificationService(repo=NotificationRepository())
    re_eval_svc = ReEvaluationService(
        repo=ReEvaluationRepository(),
        audit_service=audit_svc,
        notification_service=notification_svc,
    )
    return ClaimService(
        claim_repository=ClaimRepository(),
        income_repository=IncomeRepository(),
        expense_repository=ExpenseRepository(),
        settings_service=SettingsService(),
        re_evaluation_service=re_eval_svc,
        notification_service=notification_svc,
        audit_service=audit_svc,
        claim_note_repository=ClaimNoteRepository(),
    )


def make_re_evaluation_service():
    from services.re_evaluation_service import ReEvaluationService
    from services.notification_service import NotificationService
    from services.audit_service import AuditService
    from database.repositories.re_evaluation_repository import ReEvaluationRepository
    from database.repositories.audit_repository import AuditRepository
    from database.repositories.notification_repository import NotificationRepository

    return ReEvaluationService(
        repo=ReEvaluationRepository(),
        audit_service=AuditService(repo=AuditRepository()),
        notification_service=NotificationService(repo=NotificationRepository()),
    )


def make_checklist_service():
    from services.checklist_service import ChecklistService
    from database.repositories.checklist_repository import ChecklistRepository

    return ChecklistService(repo=ChecklistRepository())


def make_task_service():
    from services.task_service import TaskService

    return TaskService(claim_service=make_claim_service())


def make_dashboard_service():
    from services.dashboard_service import DashboardService
    from services.task_service import TaskService

    claim_svc = make_claim_service()
    return DashboardService(
        claim_service=claim_svc,
        task_service=TaskService(claim_service=claim_svc),
    )


def make_pdf_service():
    from services.pdf_service import PDFService

    return PDFService(claim_service=make_claim_service())
