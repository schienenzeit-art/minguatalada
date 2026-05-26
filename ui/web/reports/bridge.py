import os
from pathlib import Path

from PyQt6.QtCore import QObject, QUrl, pyqtSlot
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QMessageBox

from services.excel_service import ExcelService
from services.pdf_service import PDFService
from services.report_service import ReportService


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
        file_path = self.pdf_service.generate_period_report_pdf(location_id, start_date, end_date, selected_metrics)
        self._open_file_with_dialog(file_path, "PDF-Export")
        return file_path

    @pyqtSlot(int, str, str, 'QVariant', result=str)
    def export_report_excel(self, location_id: int, start_date: str, end_date: str, selected_metrics: list) -> str:
        if location_id < 0:
            location_id = None
        file_path = self.excel_service.generate_period_report_excel(location_id, start_date, end_date, selected_metrics)
        self._open_file_with_dialog(file_path, "Excel-Export")
        return file_path

    def _open_file_with_dialog(self, file_path: str, export_label: str) -> None:
        abs_path = str(Path(file_path).resolve())
        folder = str(Path(abs_path).parent)

        msg = QMessageBox()
        msg.setWindowTitle(f"{export_label} abgeschlossen")
        msg.setText(f"Der Report wurde erfolgreich erstellt.")
        msg.setInformativeText(f"Datei: {Path(abs_path).name}\nPfad: {abs_path}")
        open_btn = msg.addButton("Datei öffnen", QMessageBox.ButtonRole.AcceptRole)
        folder_btn = msg.addButton("Ordner öffnen", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Schließen", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path))
        elif msg.clickedButton() == folder_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
