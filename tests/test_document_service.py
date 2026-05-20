import unittest
from pathlib import Path

from core.session import Session
from services.document_service import DocumentService
from core.document_status import DocumentStatus


class DocumentServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = DocumentService()
        Session.set_user({"id": 1, "role_name": "Admin", "location_id": 1})
        self.source_file = Path("data/test_document_service.txt")
        self.source_file.write_text("Testinhalt für Dokumentenservice.", encoding="utf-8")
        self.document_type_id = self.service.list_document_types()[0]["id"]
        self.created_document_ids: list[int] = []

    def tearDown(self):
        Session.clear()
        if self.source_file.exists():
            self.source_file.unlink()

        for document_id in self.created_document_ids:
            try:
                file_path = self.service.get_document_path(document_id)
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass
            self.service.repository.delete_document(document_id)

    def test_create_document_stores_metadata_and_file(self):
        document = self.service.create_document(
            source_file_path=str(self.source_file),
            title="Testdokument",
            document_type_id=self.document_type_id,
            description="Eine Testbeschreibung.",
            claim_id=None,
            person_id=None,
            card_id=None,
            location_id=1,
        )
        self.created_document_ids.append(document["id"])

        self.assertEqual(document["title"], "Testdokument")
        self.assertEqual(document["status"], DocumentStatus.VORHANDEN)
        self.assertEqual(document["document_type_name"], self.service.get_document_type_by_id(self.document_type_id)["name"])
        self.assertEqual(document["original_file_name"], self.source_file.name)
        self.assertIsNotNone(document["storage_path"])

        stored_path = self.service.get_document_path(document["id"])
        self.assertTrue(stored_path.exists())
        self.assertEqual(stored_path.read_text(encoding="utf-8"), "Testinhalt für Dokumentenservice.")

    def test_list_documents_filters_by_type(self):
        document = self.service.create_document(
            source_file_path=str(self.source_file),
            title="Filterdokument",
            document_type_id=self.document_type_id,
            description=None,
            claim_id=None,
            person_id=None,
            card_id=None,
            location_id=1,
        )
        self.created_document_ids.append(document["id"])

        documents = self.service.list_documents(document_type_id=self.document_type_id)
        self.assertTrue(any(doc["id"] == document["id"] for doc in documents))

    def test_missing_source_file_raises(self):
        missing_path = Path("data/does_not_exist.pdf")
        with self.assertRaises(FileNotFoundError):
            self.service.create_document(
                source_file_path=str(missing_path),
                title="Fehlerdokument",
                document_type_id=self.document_type_id,
                description=None,
                claim_id=None,
                person_id=None,
                card_id=None,
                location_id=1,
            )

    def test_user_must_be_logged_in_to_upload(self):
        Session.clear()
        with self.assertRaises(PermissionError):
            self.service.create_document(
                source_file_path=str(self.source_file),
                title="NoUserDokument",
                document_type_id=self.document_type_id,
                description=None,
                claim_id=None,
                person_id=None,
                card_id=None,
                location_id=1,
            )


if __name__ == "__main__":
    unittest.main()
