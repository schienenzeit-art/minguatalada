from services.document_service import DocumentService
from services.location_service import LocationService
from ui.web.documents.bridge import DocumentsWebBridge
from ui.web.web_view_page import WebViewPage


class DocumentsWebPage(WebViewPage):
    def __init__(
        self,
        document_service: DocumentService | None = None,
        location_service: LocationService | None = None,
        view_mode: str = "documents",
    ):
        self.document_service = document_service or DocumentService()
        self.location_service = location_service or LocationService()
        self.bridge = DocumentsWebBridge(self.document_service, self.open_document, view_mode=view_mode)
        html_path = "ui/web/documents/index.html"
        super().__init__(html_path, self.bridge)

    def open_document(self, document: dict) -> None:
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices

        path = self.document_service.get_document_path(document["id"])
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
