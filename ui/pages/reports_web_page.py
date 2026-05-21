from services.report_service import ReportService
from ui.web.web_view_page import WebViewPage
from ui.web.reports.bridge import ReportsWebBridge


class ReportsWebPage(WebViewPage):
    def __init__(
        self,
        report_service: ReportService | None = None,
    ):
        self.report_service = report_service or ReportService()
        self.bridge = ReportsWebBridge(self.report_service)
        html_path = "ui/web/reports/index.html"
        super().__init__(html_path, self.bridge)
