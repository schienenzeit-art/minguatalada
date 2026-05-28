from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMainWindow, QMessageBox, QWidget, QHBoxLayout, QVBoxLayout

from app.container import ServiceContainer
from core.session import Session
from ui.components.app_navigation import AppNavigation
from ui.components.topbar import TopBar
from ui.pages.dashboard.dashboard_page import DashboardPage
from ui.pages.claims.claims_page import ClaimsPage
from ui.pages.tasks.tasks_page import TasksPage
from ui.pages.users.users_page import UsersPage
from ui.pages.documents.documents_page import DocumentsPage
from ui.pages.locations.locations_page import LocationsPage
from ui.pages.reports_page import ReportsPage
from ui.pages.settings.settings_page import SettingsPage
from ui.pages.cards_page import CardsPage
from ui.pages.person_dossier_page import PersonDossierPage
from ui.pages.apps.anspruchspruefung_app_page import AnspruchspruefungAppPage
from ui.pages.apps.administration_app_page import AdministrationAppPage
from ui.pages.mandants.mandants_page import MandantsPage
from ui.pages.appointments.appointments_page import AppointmentsPage
from ui.pages.archive_rules_page import ArchiveRulesPage
from ui.pages.import_page import ImportPage
from ui.pages.audit_log_page import AuditLogPage
from ui.pages.approval_page import ApprovalPage
from ui.pages.checklist_templates_page import ChecklistTemplatesPage
from ui.pages.document_templates_page import DocumentTemplatesPage
from ui.pages.role_management import RoleManagementPage
from ui.navigation.navigation_controller import NavigationController
from ui.shell.workspace_host import WorkspaceHost


class MainWindow(QMainWindow):
    def __init__(self, service_container: ServiceContainer):
        super().__init__()
        self.services = service_container
        self.current_user = Session.get_user()
        self.workspace_host = WorkspaceHost()
        self.navigation_controller = NavigationController(self.workspace_host, self.on_route_changed)
        self.topbar = None
        self.navigation = None
        self.init_ui()

    def init_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        from PyQt6.QtGui import QIcon
        from app.config import RESOURCE_DIR
        for name in ("logo.ico", "logo.png"):
            icon_path = RESOURCE_DIR / "assets" / name
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                break

        self.topbar = TopBar("Min Guata Lada", current_user=self.current_user)

        # Wire notification service to TopBar bell
        self.topbar.set_notification_service(self.services.notification_service)

        # Load available users for switching
        try:
            available_users = self.services.user_service.get_all_users()
            self.topbar.set_available_users(available_users)
        except Exception:
            pass

        self.topbar.user_changed.connect(self.on_user_changed)
        self.topbar.search_requested.connect(self.on_search_requested)

        root_layout.addWidget(self.topbar)

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.navigation = AppNavigation(self.route_to)
        body_layout.addWidget(self.navigation)

        self.setup_menu()

        # ── Core pages ────────────────────────────────────────────────────────
        self.register_route(
            "dashboard",
            DashboardPage(
                dashboard_service=self.services.dashboard_service,
                navigate_callback=self.route_to,
            ),
            title="Dashboard",
            parent_app="dashboard",
        )
        self.register_route(
            "anspruchspruefung",
            AnspruchspruefungAppPage(navigate_callback=self.route_to),
            title="Anspruchsprüfung",
            parent_app="anspruchspruefung",
        )
        self.register_route(
            "tasks",
            TasksPage(
                task_service=self.services.task_service,
                user_service=self.services.user_service,
                location_service=self.services.location_service,
                navigate_callback=self.route_to,
            ),
            title="Aufgaben",
            parent_app="tasks",
        )
        self.register_route(
            "documents",
            DocumentsPage(
                document_service=self.services.document_service,
                location_service=self.services.location_service,
            ),
            title="Dokumente",
            parent_app="documents",
        )
        self.register_route(
            "archive",
            DocumentsPage(
                document_service=self.services.document_service,
                location_service=self.services.location_service,
                archive_mode=True,
            ),
            title="Archiv",
            parent_app="documents",
        )
        self.register_route(
            "reports",
            ReportsPage(report_service=self.services.report_service),
            title="Berichte",
            parent_app="reports",
        )
        self.register_route(
            "administration",
            AdministrationAppPage(navigate_callback=self.route_to),
            title="Administration",
            parent_app="administration",
        )
        self.register_route(
            "users",
            UsersPage(user_service=self.services.user_service),
            title="Benutzer",
            parent_app="administration",
        )
        self.register_route(
            "locations",
            LocationsPage(
                location_service=self.services.location_service,
                user_service=self.services.user_service,
            ),
            title="Standorte",
            parent_app="administration",
        )
        self.register_route(
            "settings",
            SettingsPage(settings_service=self.services.settings_service),
            title="Einstellungen",
            parent_app="administration",
        )
        self.register_route(
            "claims",
            ClaimsPage(
                claim_service=self.services.claim_service,
                case_service=self.services.case_service,
                card_service=self.services.card_service,
                filter_preset_service=self.services.filter_preset_service,
            ),
            title="Anträge",
            parent_app="anspruchspruefung",
        )
        self.register_route(
            "cards",
            CardsPage(
                card_service=self.services.card_service,
                location_service=self.services.location_service,
                claim_service=self.services.claim_service,
                pdf_service=self.services.pdf_service,
            ),
            title="Karten",
            parent_app="anspruchspruefung",
        )
        self.register_route(
            "person_dossier",
            PersonDossierPage(
                person_service=self.services.person_service,
                location_service=self.services.location_service,
            ),
            title="Personendossier",
            parent_app="person_dossier",
        )

        # ── New feature pages ─────────────────────────────────────────────────
        self.register_route(
            "mandants",
            MandantsPage(mandant_service=self.services.mandant_service),
            title="Mandanten",
            parent_app="administration",
        )
        self.register_route(
            "appointments",
            AppointmentsPage(
                appointment_service=self.services.appointment_service,
                location_service=self.services.location_service,
                user_service=self.services.user_service,
            ),
            title="Termine",
            parent_app="tasks",
        )
        self.register_route(
            "archive_rules",
            ArchiveRulesPage(archive_service=self.services.archive_service),
            title="Archiv-Regeln",
            parent_app="administration",
        )
        self.register_route(
            "import",
            ImportPage(
                location_service=self.services.location_service,
                category_service=self.services.category_service,
            ),
            title="Daten-Import",
            parent_app="administration",
        )
        self.register_route(
            "audit_log",
            AuditLogPage(
                audit_service=self.services.audit_service,
                user_service=self.services.user_service,
            ),
            title="Audit-Protokoll",
            parent_app="administration",
        )
        self.register_route(
            "approvals",
            ApprovalPage(approval_service=self.services.approval_service),
            title="Freigaben",
            parent_app="tasks",
        )
        self.register_route(
            "checklist_templates",
            ChecklistTemplatesPage(
                checklist_service=self.services.checklist_service,
                category_service=self.services.category_service,
            ),
            title="Unterlagen-Checklisten",
            parent_app="administration",
        )
        self.register_route(
            "document_templates",
            DocumentTemplatesPage(
                template_service=self.services.document_template_service,
                category_service=self.services.category_service,
            ),
            title="Dokumentvorlagen",
            parent_app="documents",
        )
        self.register_route(
            "roles",
            RoleManagementPage(role_service=self.services.role_service),
            title="Rollenverwaltung",
            parent_app="administration",
        )

        self.workspace_host.set_current_page("dashboard")
        body_layout.addWidget(self.workspace_host, 1)

        root_layout.addLayout(body_layout)
        root.setLayout(root_layout)
        self.setCentralWidget(root)
        self.navigation.set_active("dashboard")
        self.topbar.set_title(self.navigation_controller.get_page_title("dashboard"))

    def setup_menu(self) -> None:
        file_menu = self.menuBar().addMenu("Datei")
        print_action = QAction("Drucken", self)
        print_action.triggered.connect(self.on_print_requested)
        file_menu.addAction(print_action)

        file_menu.addSeparator()
        exit_action = QAction("Beenden", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def on_print_requested(self) -> None:
        current_widget = self.workspace_host.stack.currentWidget()
        if current_widget is not None and hasattr(current_widget, "on_print_dossier"):
            current_widget.on_print_dossier()
            return
        QMessageBox.information(
            self, "Drucken",
            "Druckfunktion ist im aktuellen Bereich nicht verfügbar. "
            "Öffnen Sie das Personendossier, um es zu drucken.",
        )

    def register_route(self, key: str, widget: QWidget, title: str, parent_app: str | None = None) -> None:
        self.navigation_controller.register_route(key, widget, title, parent_app)

    def route_to(self, page: str, filter_context: dict | None = None) -> None:
        if page == "logout":
            self.close()
            return
        self.navigation_controller.navigate(page, filter_context)

    def on_route_changed(self, page: str) -> None:
        self.topbar.set_title(self.navigation_controller.get_page_title(page))
        self.navigation.set_active(self.navigation_controller.get_parent_app(page))

    def on_user_changed(self, user: dict) -> None:
        if user.get("logout"):
            self.close()
            return

        target_username = user.get("username", "")
        if target_username == (self.current_user or {}).get("username"):
            return

        password, ok = QInputDialog.getText(
            self,
            "Benutzer wechseln",
            f"Passwort für «{user.get('full_name', target_username)}»:",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not password:
            self.topbar.set_current_user(self.current_user)
            return

        result = self.services.auth_service.login(target_username, password)
        if not result.get("success"):
            QMessageBox.warning(self, "Fehler", result.get("message", "Anmeldung fehlgeschlagen."))
            self.topbar.set_current_user(self.current_user)
            return

        authenticated_user = result["user"]
        self.current_user = authenticated_user
        Session.set_user(authenticated_user)
        self.topbar.set_current_user(authenticated_user)
        self.route_to("dashboard")

    def on_search_requested(self, search_text: str) -> None:
        from ui.dialogs.search_result_dialog import SearchResultDialog
        dlg = SearchResultDialog(
            query=search_text,
            search_service=self.services.search_service,
            parent=self,
        )
        dlg.exec()
