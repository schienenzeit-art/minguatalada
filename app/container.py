from dataclasses import dataclass

from database.repositories.case_repository import CaseRepository
from database.repositories.category_repository import CategoryRepository
from database.repositories.claim_repository import ClaimRepository
from database.repositories.expense_repository import ExpenseRepository
from database.repositories.income_repository import IncomeRepository
from database.repositories.location_repository import LocationRepository
from database.repositories.person_repository import PersonRepository
from database.repositories.user_repository import UserRepository
from services.auth_service import AuthService
from services.card_service import CardService
from services.case_service import CaseService
from services.category_service import CategoryService
from services.claim_service import ClaimService
from services.document_service import DocumentService
from services.filter_preset_service import FilterPresetService
from services.location_service import LocationService
from services.person_service import PersonService
from services.role_service import RoleService
from services.report_service import ReportService
from services.pdf_service import PDFService
from services.search_service import SearchService
from services.user_service import UserService
from services.pruefung_service import PruefungService
from services.settings_service import SettingsService
from services.task_service import TaskService
from services.dashboard_service import DashboardService


@dataclass
class ServiceContainer:
    auth_service: AuthService
    case_service: CaseService
    claim_service: ClaimService
    settings_service: SettingsService
    user_service: UserService
    category_service: CategoryService
    location_service: LocationService
    card_service: CardService
    role_service: RoleService
    report_service: ReportService
    pdf_service: PDFService
    task_service: TaskService
    person_service: PersonService
    dashboard_service: DashboardService
    document_service: DocumentService
    search_service: SearchService
    filter_preset_service: FilterPresetService


def build_service_container() -> ServiceContainer:
    user_repository = UserRepository()
    person_repository = PersonRepository()
    case_repository = CaseRepository()
    location_repository = LocationRepository()
    category_repository = CategoryRepository()
    claim_repository = ClaimRepository()
    income_repository = IncomeRepository()
    expense_repository = ExpenseRepository()

    auth_service = AuthService(user_repository=user_repository)
    user_service = UserService(user_repository=user_repository)
    category_service = CategoryService(category_repository=category_repository)
    location_service = LocationService()
    card_service = CardService()
    settings_service = SettingsService()
    case_service = CaseService(
        person_repo=person_repository,
        case_repo=case_repository,
        location_repo=location_repository,
        category_repo=category_repository,
        settings_service=settings_service,
    )
    claim_service = ClaimService(
        claim_repository=claim_repository,
        income_repository=income_repository,
        expense_repository=expense_repository,
        settings_service=settings_service,
    )

    task_service = TaskService(
        claim_service=claim_service,
        user_service=user_service,
        location_service=location_service,
    )

    role_service = RoleService()
    report_service = ReportService()
    pdf_service = PDFService(
        claim_service=claim_service,
        card_service=card_service,
        report_service=report_service,
    )

    person_service = PersonService(person_repository=person_repository)

    dashboard_service = DashboardService(
        claim_service=claim_service,
        card_service=card_service,
        location_service=location_service,
        task_service=task_service,
    )

    document_service = DocumentService()
    search_service = SearchService()
    filter_preset_service = FilterPresetService()

    return ServiceContainer(
        auth_service=auth_service,
        case_service=case_service,
        claim_service=claim_service,
        settings_service=settings_service,
        user_service=user_service,
        category_service=category_service,
        location_service=location_service,
        card_service=card_service,
        task_service=task_service,
        person_service=person_service,
        role_service=role_service,
        report_service=report_service,
        pdf_service=pdf_service,
        dashboard_service=dashboard_service,
        document_service=document_service,
        search_service=search_service,
        filter_preset_service=filter_preset_service,
    )
