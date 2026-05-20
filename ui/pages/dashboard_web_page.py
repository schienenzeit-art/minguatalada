from typing import Callable

from services.dashboard_service import DashboardService
from ui.web.web_view_page import WebViewPage
from ui.web.dashboard.bridge import DashboardWebBridge


class DashboardWebPage(WebViewPage):
    def __init__(
        self,
        dashboard_service: DashboardService | None = None,
        navigate_callback: Callable[[str, dict | None], None] | None = None,
    ):
        self.dashboard_service = dashboard_service or DashboardService()
        self.bridge = DashboardWebBridge(self.dashboard_service, navigate_callback)
        html_path = "ui/web/dashboard/index.html"
        super().__init__(html_path, self.bridge)
