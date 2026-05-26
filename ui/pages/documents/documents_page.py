from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QDialog,
)
from ui.components.table_widget import TableWidget

from core.document_status import DocumentStatus
from services.document_service import DocumentService
from services.location_service import LocationService
from ui.components.page_header import PageHeader
from ui.pages.documents.document_dialog import DocumentDialog


class DocumentsPage(QWidget):
    def __init__(
        self,
        document_service: DocumentService | None = None,
        location_service: LocationService | None = None,
    ):
        super().__init__()
        self.document_service = document_service or DocumentService()
        self.location_service = location_service or LocationService()
        self.document_id_filter: int | None = None
        self.setup_ui()
        self.load_filters()
        self.refresh_documents()

    def setup_ui(self):
        self.setObjectName("documentsPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = PageHeader(
            title="Dokumente & Archiv",
            subtitle="Verwalten Sie Nachweise, Dokumente und zugeordnete Verbindungen zu Fällen, Personen, Karten und Standorten.",
            action_text="Dokument hochladen",
            action_callback=self.open_upload_dialog,
        )
        layout.addWidget(header)

        filter_layout_top = QHBoxLayout()
        filter_layout_top.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Suche nach Titel, Dateiname, Bezug oder Typ")
        self.search_input.textChanged.connect(self.refresh_documents)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Alle Typen", None)
        self.type_combo.currentIndexChanged.connect(self.refresh_documents)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Alle Status", None)
        for status in DocumentStatus.ALL_STATUSES:
            self.status_combo.addItem(DocumentStatus.get_display(status), status)
        self.status_combo.currentIndexChanged.connect(self.refresh_documents)

        self.location_combo = QComboBox()
        self.location_combo.addItem("Alle Standorte", None)
        self.location_combo.currentIndexChanged.connect(self.refresh_documents)

        filter_layout_top.addWidget(self.search_input)
        filter_layout_top.addWidget(QLabel("Typ:"))
        filter_layout_top.addWidget(self.type_combo)
        filter_layout_top.addWidget(QLabel("Status:"))
        filter_layout_top.addWidget(self.status_combo)
        filter_layout_top.addWidget(QLabel("Standort:"))
        filter_layout_top.addWidget(self.location_combo)

        filter_layout_bottom = QHBoxLayout()
        filter_layout_bottom.setSpacing(12)

        self.claim_id_input = QLineEdit()
        self.claim_id_input.setPlaceholderText("Fall-ID")
        self.claim_id_input.textChanged.connect(self.refresh_documents)

        self.person_id_input = QLineEdit()
        self.person_id_input.setPlaceholderText("Personen-ID")
        self.person_id_input.textChanged.connect(self.refresh_documents)

        self.card_id_input = QLineEdit()
        self.card_id_input.setPlaceholderText("Karten-ID")
        self.card_id_input.textChanged.connect(self.refresh_documents)

        self.date_from_input = QLineEdit()
        self.date_from_input.setPlaceholderText("Von (YYYY-MM-DD)")
        self.date_from_input.textChanged.connect(self.refresh_documents)

        self.date_to_input = QLineEdit()
        self.date_to_input.setPlaceholderText("Bis (YYYY-MM-DD)")
        self.date_to_input.textChanged.connect(self.refresh_documents)

        self.refresh_button = QPushButton("Aktualisieren")
        self.refresh_button.clicked.connect(self.refresh_documents)

        filter_layout_bottom.addWidget(self.claim_id_input)
        filter_layout_bottom.addWidget(self.person_id_input)
        filter_layout_bottom.addWidget(self.card_id_input)
        filter_layout_bottom.addWidget(self.date_from_input)
        filter_layout_bottom.addWidget(self.date_to_input)
        filter_layout_bottom.addWidget(self.refresh_button)

        self.table = TableWidget(11)
        self.table.setHorizontalHeaderLabels([
            "Titel",
            "Typ",
            "Bezug",
            "Status",
            "Hochgeladen",
            "Standort",
            "Dateiname",
            "Größe",
            "Ersteller",
            "Öffnen",
            "Archivieren",
        ])
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)

        layout.addLayout(filter_layout_top)
        layout.addLayout(filter_layout_bottom)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_filters(self):
        self.type_combo.clear()
        self.type_combo.addItem("Alle Typen", None)
        for document_type in self.document_service.list_document_types():
            self.type_combo.addItem(document_type["name"], document_type["id"])

        self.location_combo.clear()
        self.location_combo.addItem("Alle Standorte", None)
        for location in self.location_service.list_active_locations():
            self.location_combo.addItem(location["name"], location["id"])

    def refresh_documents(self):
        document_type_id = self.type_combo.currentData()
        status = self.status_combo.currentData()
        claim_id = int(self.claim_id_input.text().strip()) if self.claim_id_input.text().strip().isdigit() else None
        person_id = int(self.person_id_input.text().strip()) if self.person_id_input.text().strip().isdigit() else None
        card_id = int(self.card_id_input.text().strip()) if self.card_id_input.text().strip().isdigit() else None
        location_id = self.location_combo.currentData()

        uploaded_from = self._normalize_date(self.date_from_input.text().strip())
        uploaded_to = self._normalize_date(self.date_to_input.text().strip(), end_of_day=True)

        self.documents = self.document_service.list_documents(
            search_text=self.search_input.text().strip() or None,
            document_type_id=document_type_id,
            status=status,
            claim_id=claim_id,
            person_id=person_id,
            card_id=card_id,
            location_id=location_id,
            uploaded_from=uploaded_from,
            uploaded_to=uploaded_to,
            document_id=self.document_id_filter,
        )
        self.document_id_filter = None
        self.render_table()

    def render_table(self):
        self.table.setRowCount(len(self.documents))

        for row_index, document in enumerate(self.documents):
            self.table.setItem(row_index, 0, QTableWidgetItem(document["title"]))
            self.table.setItem(row_index, 1, QTableWidgetItem(document.get("document_type_name", "-")))
            self.table.setItem(row_index, 2, QTableWidgetItem(self._format_reference(document)))
            self.table.setItem(row_index, 3, QTableWidgetItem(DocumentStatus.get_display(document.get("status", ""))))
            self.table.setItem(row_index, 4, QTableWidgetItem(document.get("uploaded_at", "-")))
            self.table.setItem(row_index, 5, QTableWidgetItem(document.get("location_name", "-")))
            self.table.setItem(row_index, 6, QTableWidgetItem(document.get("original_file_name", "-")))
            self.table.setItem(row_index, 7, QTableWidgetItem(str(document.get("file_size", "-"))))
            self.table.setItem(row_index, 8, QTableWidgetItem(document.get("uploaded_by_name", "-")))

            open_button = QPushButton("Öffnen")
            open_button.clicked.connect(lambda _, d=document: self.open_document(d))
            self.table.setCellWidget(row_index, 9, open_button)

            # Archive button (skip if already archived)
            if document.get("status") != "ARCHIVIERT":
                archive_button = QPushButton("Archivieren")
                archive_button.clicked.connect(lambda _, d=document: self.on_archive_document(d))
                self.table.setCellWidget(row_index, 10, archive_button)
            else:
                # Show disabled button or label if already archived
                archived_label = QTableWidgetItem("Archiviert")
                self.table.setItem(row_index, 10, archived_label)

    def open_upload_dialog(self):
        dialog = DocumentDialog(self.document_service, self.location_service)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()
        try:
            self.document_service.create_document(**data)
            QMessageBox.information(self, "Erfolg", "Dokument wurde hochgeladen.")
            self.load_filters()
            self.refresh_documents()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Dokument konnte nicht hochgeladen werden: {e}")

    def open_document(self, document: dict) -> None:
        try:
            path = self.document_service.get_document_path(document["id"])
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Fehler", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Dokument konnte nicht geöffnet werden: {e}")

    def on_archive_document(self, document: dict) -> None:
        """Archive a document manually."""
        reply = QMessageBox.question(
            self,
            "Archivieren bestätigen",
            f"Möchten Sie das Dokument '{document.get('title', '-')}' archivieren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self.document_service.archive_document(document["id"])
            QMessageBox.information(self, "Erfolg", "Dokument wurde archiviert.")
            self.refresh_documents()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Dokument konnte nicht archiviert werden: {e}")

    def on_row_double_clicked(self, row: int, column: int) -> None:
        document = self.documents[row]
        self.open_document(document)

    def _format_reference(self, document: dict) -> str:
        references = []
        if document.get("claim_case_number"):
            references.append(f"Fall {document['claim_case_number']}")
        if document.get("person_name"):
            references.append(f"Person {document['person_name']}")
        if document.get("card_number"):
            references.append(f"Karte {document['card_number']}")
        if document.get("location_name"):
            references.append(f"Standort {document['location_name']}")
        return ", ".join(references) if references else "-"

    def _normalize_date(self, value: str, end_of_day: bool = False) -> str | None:
        if not value:
            return None
        parts = value.split("-")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            return None
        year, month, day = parts
        if end_of_day:
            return f"{year}-{month}-{day}T23:59:59.999999"
        return f"{year}-{month}-{day}T00:00:00"

    def apply_filters(
        self,
        document_id: int | None = None,
        claim_id: int | None = None,
        person_id: int | None = None,
        card_id: int | None = None,
        location_id: int | None = None,
    ) -> None:
        self.document_id_filter = document_id

        if claim_id is not None:
            self.claim_id_input.setText(str(claim_id))
        if person_id is not None:
            self.person_id_input.setText(str(person_id))
        if card_id is not None:
            self.card_id_input.setText(str(card_id))
        if location_id is not None:
            for index in range(self.location_combo.count()):
                if self.location_combo.itemData(index) == location_id:
                    self.location_combo.setCurrentIndex(index)
                    break

        self.refresh_documents()
