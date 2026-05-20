from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget

from app.container import ServiceContainer
from core.session import Session
from ui.components.sidebar import Sidebar
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
from ui.pages.apps.anspruchspruefung_app_page import AnspruchspruefungAppPage
from ui.pages.apps.administration_app_page import AdministrationAppPage


class MainWindow(QMainWindow):
    def __init__(self, service_container: ServiceContainer):
        super().__init__()
        self.services = service_container
        self.current_user = Session.get_user()
        self.pages = {}
        self.stack = QStackedWidget()
        self.sidebar = None
        self.topbar = None
        self.init_ui()

    def init_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.topbar = TopBar("Dashboard")
        root_layout.addWidget(self.topbar)

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.sidebar = Sidebar(self.navigate)
        body_layout.addWidget(self.sidebar)

        self.register_page(
            "dashboard",
            DashboardPage(
                dashboard_service=self.services.dashboard_service,
                navigate_callback=self.navigate,
            ),
        )
        self.register_page(
            "anspruchspruefung",
            AnspruchspruefungAppPage(navigate_callback=self.navigate),
        )
        self.register_page(
            "tasks",
            TasksPage(
                task_service=self.services.task_service,
                user_service=self.services.user_service,
                location_service=self.services.location_service,
                navigate_callback=self.navigate,
            ),
        )
        self.register_page(
            "documents",
            DocumentsPage(
                document_service=self.services.document_service,
                location_service=self.services.location_service,
            ),
        )
        self.register_page(
            "reports",
            ReportsPage(report_service=self.services.report_service),
        )
        self.register_page(
            "administration",
            AdministrationAppPage(navigate_callback=self.navigate),
        )
        self.register_page("users", UsersPage(user_service=self.services.user_service))
        self.register_page(
            "locations",
            LocationsPage(
                location_service=self.services.location_service,
                user_service=self.services.user_service,
            ),
        )
        self.register_page(
            "settings",
            SettingsPage(settings_service=self.services.settings_service),
        )
        self.register_page(
            "claims",
            ClaimsPage(
                claim_service=self.services.claim_service,
                case_service=self.services.case_service,
                card_service=self.services.card_service,
            ),
        )
        self.register_page(
            "cards",
            CardsPage(
                card_service=self.services.card_service,
                location_service=self.services.location_service,
                claim_service=self.services.claim_service,
            ),
        )

        self.stack.setCurrentWidget(self.pages["dashboard"])
        body_layout.addWidget(self.stack, 1)

        root_layout.addLayout(body_layout)
        root.setLayout(root_layout)
        self.setCentralWidget(root)
        self.sidebar.set_active("dashboard")

    def register_page(self, key: str, widget: QWidget) -> None:
        self.pages[key] = widget
        self.stack.addWidget(widget)

    def navigate(self, page: str, filter_context: dict | None = None) -> None:
        if page == "logout":
            self.close()
            return

        page_widget = self.pages.get(page)
        if page_widget:
            if filter_context and hasattr(page_widget, "apply_filters"):
                page_widget.apply_filters(**filter_context)
            self.stack.setCurrentWidget(page_widget)
            self.topbar.set_title(self.get_page_title(page))
            self.set_active_app_for(page)

    def set_active_app_for(self, page: str) -> None:
        parent_page = {
            "claims": "anspruchspruefung",
            "cards": "anspruchspruefung",
            "tasks": "tasks",
            "documents": "documents",
            "reports": "reports",
            "users": "administration",
            "locations": "administration",
            "settings": "administration",
            "anspruchspruefung": "anspruchspruefung",
            "administration": "administration",
            "dashboard": "dashboard",
        }.get(page, page)

        self.sidebar.set_active(parent_page)

    def get_page_title(self, page: str) -> str:
        titles = {
            "dashboard": "Dashboard",
            "claims": "Anträge",
            "tasks": "Aufgaben",
            "users": "Benutzer",
            "documents": "Dokumente",
            "locations": "Standorte",
            "cards": "Karten",
            "reports": "Berichte",
            "settings": "Einstellungen",
        }
        return titles.get(page, "Anspruchssystem")
