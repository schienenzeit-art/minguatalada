from PyQt6.QtCore import QObject, pyqtSlot
from services.pdf_service import PDFService
from services.report_service import ReportService
from services.excel_service import ExcelService


class ReportsWebBridge(QObject):
    def __init__(self, report_service: ReportService | None = None):
        super().__init__()
        self.report_service = report_service or ReportService()
        self.pdf_service = PDFService(report_service=self.report_service)
        self.excel_service = ExcelService(report_service=self.report_service)

    @pyqtSlot(result=list)
    def get_locations(self) -> list:
        return self.report_service.get_locations(include_inactive=False)

    @pyqtSlot(int, str, str, result='QVariant')
    def get_period_report(self, location_id: int, start_date: str, end_date: str) -> dict:
        if location_id < 0:
            location_id = None
        return self.report_service.get_period_report(start_date, end_date, location_id)

    @pyqtSlot(int, str, str, 'QVariant', result=str)
    def export_report_pdf(self, location_id: int, start_date: str, end_date: str, selected_metrics: list) -> str:
        if location_id < 0:
            location_id = None
        return self.pdf_service.generate_period_report_pdf(location_id, start_date, end_date, selected_metrics)

    @pyqtSlot(int, str, str, 'QVariant', result=str)
    def export_report_excel(self, location_id: int, start_date: str, end_date: str, selected_metrics: list) -> str:
        if location_id < 0:
            location_id = None
        return self.excel_service.generate_period_report_excel(location_id, start_date, end_date, selected_metrics)
