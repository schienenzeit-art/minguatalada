from PyQt6.QtCore import QObject, pyqtSlot
from services.document_service import DocumentService
from core.document_status import DocumentStatus
from pathlib import Path
import os


class DocumentsWebBridge(QObject):
    def __init__(
        self,
        document_service: DocumentService,
        open_document_callback=None,
        view_mode: str = "documents",
    ):
        super().__init__()
        self.document_service = document_service
        self.open_document_callback = open_document_callback
        self.view_mode = view_mode

    @pyqtSlot(str, str, int, result=list)
    def list_documents(self, search_text: str, status: str, location_id: int) -> list:
        if status == "":
            status = None
        if location_id == -1:
            location_id = None

        documents = self.document_service.list_documents(
            search_text=search_text or None,
            status=status or None,
            location_id=location_id,
        )
        return [self._serialize_document(doc) for doc in documents]

    @pyqtSlot(int, str, result=bool)
    def rename_document(self, document_id: int, new_title: str) -> bool:
        if not new_title or not str(new_title).strip():
            return False
        return self.document_service.update_document_title(document_id, str(new_title).strip())

    @pyqtSlot(int)
    def open_document(self, document_id: int) -> None:
        document = self.document_service.get_document_by_id(document_id)
        if not document:
            return
        if self.open_document_callback:
            self.open_document_callback(document)

    @pyqtSlot(result=str)
    def get_view_mode(self) -> str:
        return self.view_mode

    @pyqtSlot(result=list)
    def get_locations(self) -> list:
        from services.location_service import LocationService

        locations = LocationService().list_active_locations()
        return [
            {
                "id": location["id"],
                "name": location["name"],
            }
            for location in locations
        ]

    def _serialize_document(self, doc: dict) -> dict:
        return {
            "id": doc.get("id"),
            "title": doc.get("title") or "-",
            "document_type_name": doc.get("document_type_name") or "-",
            "reference": self._format_reference(doc),
            "status": DocumentStatus.get_display(doc.get("status", "")),
            "uploaded_at": doc.get("uploaded_at") or "-",
            "location_name": doc.get("location_name") or "-",
            "original_file_name": doc.get("original_file_name") or "-",
            "person_name": doc.get("person_name") or "Nicht zugeordnet",
        }

    def _format_reference(self, document: dict) -> str:
        references = []
        if document.get("claim_case_number"):
            references.append(f"Fall {document['claim_case_number']}")
        if document.get("person_name"):
            references.append(document["person_name"])
        if document.get("location_name"):
            references.append(document["location_name"])
        return ", ".join(references) if references else "-"
