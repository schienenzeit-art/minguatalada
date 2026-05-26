from __future__ import annotations

import json
import mimetypes
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.config import DOCUMENTS_DIR
from core.document_status import DocumentStatus
from core.session import Session
from database.db import get_connection
from database.repositories.document_repository import DocumentRepository
from database.repositories.document_type_repository import DocumentTypeRepository


DEFAULT_DOCUMENT_TYPES = [
    "Ausweis",
    "Einkommensnachweis",
    "Haushaltsnachweis",
    "Antrag",
    "Prüfprotokoll",
    "Bescheid",
    "Kartenunterlage",
    "Sonstiges",
]


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository | None = None,
        type_repository: DocumentTypeRepository | None = None,
    ):
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        self.repository = repository or DocumentRepository()
        self.type_repository = type_repository or DocumentTypeRepository()
        self._seed_document_types()

    def _seed_document_types(self) -> None:
        for name in DEFAULT_DOCUMENT_TYPES:
            self.type_repository.create_document_type(name=name)

    def list_document_types(self, include_inactive: bool = False) -> List[Dict[str, object]]:
        return self.type_repository.list_document_types(include_inactive=include_inactive)

    def get_document_type_by_id(self, document_type_id: int) -> Optional[Dict[str, object]]:
        return self.type_repository.get_document_type_by_id(document_type_id)

    def list_documents(
        self,
        search_text: str | None = None,
        document_type_id: int | None = None,
        status: str | None = None,
        claim_id: int | None = None,
        person_id: int | None = None,
        card_id: int | None = None,
        location_id: int | None = None,
        uploaded_from: str | None = None,
        uploaded_to: str | None = None,
        document_id: int | None = None,
    ) -> List[Dict[str, object]]:
        if not Session.is_admin() and location_id is None:
            user = Session.get_user() or {}
            location_id = user.get("location_id")

        return self.repository.list_documents(
            search_text=search_text,
            document_type_id=document_type_id,
            status=status,
            claim_id=claim_id,
            person_id=person_id,
            card_id=card_id,
            location_id=location_id,
            uploaded_from=uploaded_from,
            uploaded_to=uploaded_to,
            document_id=document_id,
        )

    def get_document_by_id(self, document_id: int) -> Optional[Dict[str, object]]:
        return self.repository.get_document_by_id(document_id)

    def update_document_title(self, document_id: int, title: str) -> bool:
        return self.repository.update_document_title(document_id, title)

    def archive_document(self, document_id: int) -> bool:
        """Archive a document manually (sets status to ARCHIVIERT)."""
        archived = self.repository.update_document_status(document_id, "ARCHIVIERT")
        if archived:
            self._record_audit_log(
                user_id=Session.get_user_id(),
                action="archive_document",
                object_type="document",
                object_id=document_id,
                details={"document_id": document_id},
            )
        return archived

    def delete_document(self, document_id: int) -> bool:
        deleted = self.repository.delete_document(document_id)
        if deleted:
            self._record_audit_log(
                user_id=Session.get_user_id(),
                action="delete_document",
                object_type="document",
                object_id=document_id,
                details={"document_id": document_id},
            )
        return deleted

    def create_document(
        self,
        source_file_path: str,
        title: str,
        document_type_id: int,
        description: str | None = None,
        claim_id: int | None = None,
        person_id: int | None = None,
        card_id: int | None = None,
        location_id: int | None = None,
    ) -> Dict[str, object]:
        if Session.get_user_id() is None:
            raise PermissionError("Zum Hochladen von Dokumenten müssen Sie angemeldet sein.")

        document_type = self.get_document_type_by_id(document_type_id)
        if document_type is None or not document_type["is_active"]:
            raise ValueError("Ungültiger Dokumenttyp.")

        source_path = Path(source_file_path)
        if not source_path.exists() or not source_path.is_file():
            raise FileNotFoundError("Quell-Datei wurde nicht gefunden.")

        storage_path, file_name = self._build_storage_path(source_path.name, document_type["name"])
        target_path = DOCUMENTS_DIR / storage_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)

        mime_type, _ = mimetypes.guess_type(target_path.name)
        mime_type = mime_type or "application/octet-stream"
        file_size = target_path.stat().st_size
        now = datetime.utcnow().isoformat()

        document_id = self.repository.create_document(
            title=title.strip() or source_path.stem,
            original_file_name=source_path.name,
            file_name=file_name,
            storage_path=str(storage_path),
            mime_type=mime_type,
            file_size=file_size,
            document_type_id=document_type_id,
            status=DocumentStatus.VORHANDEN,
            description=description.strip() if description else None,
            claim_id=claim_id,
            person_id=person_id,
            card_id=card_id,
            location_id=location_id,
            uploaded_by=Session.get_user_id(),
            uploaded_at=now,
            updated_at=now,
        )

        self._record_audit_log(
            user_id=Session.get_user_id(),
            action="upload_document",
            object_type="document",
            object_id=document_id,
            details={
                "file_name": file_name,
                "original_file_name": source_path.name,
                "document_type_id": document_type_id,
                "claim_id": claim_id,
                "person_id": person_id,
                "card_id": card_id,
                "location_id": location_id,
            },
        )

        return self.get_document_by_id(document_id)

    def get_document_path(self, document_id: int) -> Path:
        document = self.get_document_by_id(document_id)
        if document is None:
            raise KeyError(f"Dokument mit ID {document_id} wurde nicht gefunden.")

        storage_path = Path(document["storage_path"])
        absolute_path = storage_path if storage_path.is_absolute() else DOCUMENTS_DIR / storage_path
        if not absolute_path.exists():
            raise FileNotFoundError("Die Datei zum Dokument konnte nicht gefunden werden.")

        return absolute_path

    def _build_storage_path(self, original_name: str, document_type_name: str) -> tuple[Path, str]:
        safe_type = self._sanitize_component(document_type_name)
        safe_base = self._sanitize_component(Path(original_name).stem)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        suffix = Path(original_name).suffix
        file_name = f"{timestamp}_{unique_id}_{safe_base}{suffix}"
        storage_path = Path(safe_type) / datetime.utcnow().strftime("%Y") / file_name
        return storage_path, file_name

    def _sanitize_component(self, value: str) -> str:
        normalized = value.strip().replace(" ", "_")
        normalized = re.sub(r"[^a-zA-Z0-9_\-\.]+", "", normalized)
        return normalized[:128]

    def _record_audit_log(
        self,
        user_id: int | None,
        action: str,
        object_type: str,
        object_id: int,
        details: Dict[str, object],
    ) -> None:
        payload = json.dumps(details, ensure_ascii=False)
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO audit_logs (user_id, action, object_type, object_id, details) VALUES (?, ?, ?, ?, ?)",
                (user_id, action, object_type, object_id, payload),
            )
            connection.commit()
