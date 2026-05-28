from dataclasses import dataclass

from database.repositories.case_repository import CaseRepository
from database.repositories.category_repository import CategoryRepository
from database.repositories.claim_repository import ClaimRepository
from database.repositories.expense_repository import ExpenseRepository
from database.repositories.income_repository import IncomeRepository
from database.repositories.location_repository import LocationRepository
from database.repositories.person_repository import PersonRepository
from database.repositories.user_repository import UserRepository
from database.repositories.appointment_repository import AppointmentRepository
from database.repositories.archive_repository import ArchiveRepository
from database.repositories.person_note_repository import PersonNoteRepository
from database.repositories.notification_repository import NotificationRepository
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
from services.mandant_service import MandantService
from services.notification_service import NotificationService
from services.appointment_service import AppointmentService
from services.archive_service import ArchiveService
from services.person_note_service import PersonNoteService
from services.audit_service import AuditService
from services.approval_service import ApprovalService
from services.checklist_service import ChecklistService
from services.document_template_service import DocumentTemplateService
from services.age_alert_service import AgeAlertService
from services.household_service import HouseholdService
from services.ocr_service import OcrService
from services.update_service import UpdateService
from services.re_evaluation_service import ReEvaluationService
from services.user_mail_service import UserMailService
from services.wiedervorlage_service import WiedervorlageService
from services.document_package_service import DocumentPackageService
from database.repositories.user_mail_config_repository import UserMailConfigRepository
from database.repositories.wiedervorlage_repository import WiedervorlageRepository
from database.repositories.audit_repository import AuditRepository
from database.repositories.approval_repository import ApprovalRepository
from database.repositories.checklist_repository import ChecklistRepository
from database.repositories.document_template_repository import DocumentTemplateRepository
from database.repositories.household_member_repository import HouseholdMemberRepository
from database.repositories.re_evaluation_repository import ReEvaluationRepository


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
    mandant_service: MandantService
    notification_service: NotificationService
    appointment_service: AppointmentService
    archive_service: ArchiveService
    person_note_service: PersonNoteService
    audit_service: AuditService
    approval_service: ApprovalService
    checklist_service: ChecklistService
    document_template_service: DocumentTemplateService
    age_alert_service: AgeAlertService
    household_service: HouseholdService
    ocr_service: OcrService
    update_service: UpdateService
    re_evaluation_service: ReEvaluationService
    user_mail_service: UserMailService
    wiedervorlage_service: WiedervorlageService
    document_package_service: DocumentPackageService


def build_service_container() -> ServiceContainer:
    user_repository     = UserRepository()
    person_repository   = PersonRepository()
    case_repository     = CaseRepository()
    location_repository = LocationRepository()
    category_repository = CategoryRepository()
    claim_repository    = ClaimRepository()
    income_repository   = IncomeRepository()
    expense_repository  = ExpenseRepository()

    auth_service     = AuthService(user_repository=user_repository)
    user_service     = UserService(user_repository=user_repository)
    category_service = CategoryService(category_repository=category_repository)
    location_service = LocationService()
    card_service     = CardService()
    settings_service = SettingsService()

    case_service = CaseService(
        person_repo=person_repository,
        case_repo=case_repository,
        location_repo=location_repository,
        category_repo=category_repository,
        settings_service=settings_service,
    )
    re_evaluation_service = ReEvaluationService(repo=ReEvaluationRepository())

    audit_service_early   = AuditService(repo=AuditRepository())
    notification_service_early = NotificationService(repo=NotificationRepository())

    claim_service = ClaimService(
        claim_repository=claim_repository,
        income_repository=income_repository,
        expense_repository=expense_repository,
        settings_service=settings_service,
        re_evaluation_service=re_evaluation_service,
        notification_service=notification_service_early,
        audit_service=audit_service_early,
    )

    task_service = TaskService(
        claim_service=claim_service,
        user_service=user_service,
        location_service=location_service,
    )

    role_service   = RoleService()
    report_service = ReportService()
    pdf_service    = PDFService(
        claim_service=claim_service,
        card_service=card_service,
        report_service=report_service,
    )

    person_service   = PersonService(person_repository=person_repository)

    dashboard_service = DashboardService(
        claim_service=claim_service,
        card_service=card_service,
        location_service=location_service,
        task_service=task_service,
    )

    document_service      = DocumentService()
    search_service        = SearchService()
    filter_preset_service = FilterPresetService()

    mandant_service           = MandantService()
    notification_service      = NotificationService(repo=NotificationRepository())
    appointment_service       = AppointmentService(repo=AppointmentRepository())
    archive_service           = ArchiveService(repo=ArchiveRepository())
    person_note_service       = PersonNoteService(repo=PersonNoteRepository())
    audit_service             = AuditService(repo=AuditRepository())
    approval_service          = ApprovalService(repo=ApprovalRepository())
    checklist_service         = ChecklistService(repo=ChecklistRepository())
    document_template_service = DocumentTemplateService(repo=DocumentTemplateRepository())

    age_alert_service        = AgeAlertService()
    household_service        = HouseholdService()
    ocr_service              = OcrService()
    update_service           = UpdateService(settings_service=settings_service)
    user_mail_service        = UserMailService(repo=UserMailConfigRepository())
    wiedervorlage_service    = WiedervorlageService(repo=WiedervorlageRepository())
    document_package_service = DocumentPackageService(
        pdf_service=pdf_service,
        template_service=document_template_service,
    )

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
        mandant_service=mandant_service,
        notification_service=notification_service,
        appointment_service=appointment_service,
        archive_service=archive_service,
        person_note_service=person_note_service,
        audit_service=audit_service,
        approval_service=approval_service,
        checklist_service=checklist_service,
        document_template_service=document_template_service,
        age_alert_service=age_alert_service,
        household_service=household_service,
        ocr_service=ocr_service,
        update_service=update_service,
        re_evaluation_service=re_evaluation_service,
        user_mail_service=user_mail_service,
        wiedervorlage_service=wiedervorlage_service,
        document_package_service=document_package_service,
    )
