from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox

from app.container import ServiceContainer
from core.session import Session
from ui.components.app_navigation import AppNavigation
from ui.components.topbar import TopBar
from ui.pages.dashboard.dashboard_page import DashboardPage
from ui.pages.claims.claims_page import ClaimsPage
from ui.pages.tasks.tasks_page import TasksPage
from ui.pages.users.users_page import UsersPage
from ui.pages.documents_web_page import DocumentsWebPage
from ui.pages.locations.locations_page import LocationsPage
from ui.pages.reports_web_page import ReportsWebPage
from ui.pages.settings.settings_page import SettingsPage
from ui.pages.cards_page import CardsPage
from ui.pages.apps.anspruchspruefung_app_page import AnspruchspruefungAppPage
from ui.pages.apps.administration_app_page import AdministrationAppPage
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

        self.topbar = TopBar("Startcockpit")
        root_layout.addWidget(self.topbar)

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.navigation = AppNavigation(self.route_to)
        body_layout.addWidget(self.navigation)

        self.setup_menu()

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
            DocumentsWebPage(
                document_service=self.services.document_service,
                location_service=self.services.location_service,
                view_mode="documents",
            ),
            title="Dokumente",
            parent_app="documents",
        )
        self.register_route(
            "archive",
            DocumentsWebPage(
                document_service=self.services.document_service,
                location_service=self.services.location_service,
                view_mode="archive",
            ),
            title="Archiv",
            parent_app="documents",
        )
        self.register_route(
            "reports",
            ReportsWebPage(report_service=self.services.report_service),
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
            ),
            title="Karten",
            parent_app="anspruchspruefung",
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

        QMessageBox.information(self, "Drucken", "Druckfunktion ist im aktuellen Bereich nicht verfügbar. Öffnen Sie das Personendossier, um es zu drucken.")

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
