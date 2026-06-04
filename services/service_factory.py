"""Zentrale Fabrik-Funktionen für Service-Instanzen ohne DI-Container.

Verwendung: UI-Komponenten die Services als Optional-Parameter enthalten
und einen sicheren Fallback benötigen, falls kein Container vorhanden ist.

In normaler Produktions-Ausführung werden Services immer über den
ServiceContainer (build_service_container) injiziert – diese Funktionen
sind nur Fallback für Edge Cases (Demo-Screens, manuelle Instanziierung).
"""
from __future__ import annotations


def default_claim_service():
    """Vollständig verdrahteter ClaimService ohne externen DI-Container."""
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

    audit_svc = AuditService(repo=AuditRepository())
    return ClaimService(
        claim_repository=ClaimRepository(),
        income_repository=IncomeRepository(),
        expense_repository=ExpenseRepository(),
        settings_service=SettingsService(),
        re_evaluation_service=ReEvaluationService(repo=ReEvaluationRepository(), audit_service=audit_svc),
        notification_service=NotificationService(repo=NotificationRepository()),
        audit_service=audit_svc,
    )


def default_re_eval_service():
    """Vollständig verdrahteter ReEvaluationService ohne externen DI-Container."""
    from services.re_evaluation_service import ReEvaluationService
    from database.repositories.re_evaluation_repository import ReEvaluationRepository

    return ReEvaluationService(repo=ReEvaluationRepository())
