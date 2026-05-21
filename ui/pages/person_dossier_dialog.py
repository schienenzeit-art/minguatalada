from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QGroupBox,
    QPushButton,
    QComboBox,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QFileDialog,
    QTableWidgetItem,
    QHeaderView,
)

from ui.components.table_widget import TableWidget
from services.claim_service import ClaimService
from services.document_service import DocumentService
from services.pdf_service import PDFService
from database.repositories.person_repository import PersonRepository


class PersonDossierDialog(QDialog):
    def __init__(
        self,
        person_id: int,
        claim_service: ClaimService | None = None,
        document_service: DocumentService | None = None,
        pdf_service: PDFService | None = None,
    ):
        super().__init__()
        self.person_id = person_id
        self.claim_service = claim_service or ClaimService()
        self.document_service = document_service or DocumentService()
        self.pdf_service = pdf_service or PDFService(document_service=self.document_service)
        self.person_repository = PersonRepository()
        self.selected_files: list[str] = []

        self.setWindowTitle("Personendossier")
        self.setMinimumSize(960, 700)

        self.setup_ui()
        self.load_person()
        self.load_claims()
        self.refresh_documents()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Personendossier")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Persönliche Daten, Fälle, Dokumente und Dossierdruck")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #52606d;")

        header_box = QGroupBox()
        header_layout = QVBoxLayout()
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_box.setLayout(header_layout)

        person_box = QGroupBox("Personendaten")
        person_form = QFormLayout()
        person_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        person_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        person_form.setHorizontalSpacing(20)
        person_form.setVerticalSpacing(12)

        self.name_label = QLabel("-")
        self.birthdate_label = QLabel("-")
        self.address_label = QLabel("-")
        self.city_label = QLabel("-")
        self.email_label = QLabel("-")

        for label in [self.name_label, self.birthdate_label, self.address_label, self.city_label, self.email_label]:
            label.setWordWrap(True)

        person_form.addRow("Name:", self.name_label)
        person_form.addRow("Geburtsdatum:", self.birthdate_label)
        person_form.addRow("Adresse:", self.address_label)
        person_form.addRow("Ort:", self.city_label)
        person_form.addRow("E-Mail:", self.email_label)
        person_box.setLayout(person_form)

        claims_box = QGroupBox("Verknüpfte Fälle")
        claims_layout = QVBoxLayout()
        self.claims_label = QLabel("-")
        self.claims_label.setWordWrap(True)
        claims_layout.addWidget(self.claims_label)
        claims_box.setLayout(claims_layout)

        document_card = QGroupBox("Dokumente")
        document_layout = QVBoxLayout()
        document_layout.setSpacing(12)

        upload_form = QFormLayout()
        upload_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        upload_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        upload_form.setHorizontalSpacing(20)
        upload_form.setVerticalSpacing(12)

        self.document_type_combo = QComboBox()
        self.document_description_input = QLineEdit()
        self.document_description_input.setPlaceholderText("Beschreibung (optional)")
        for document_type in self.document_service.list_document_types():
            self.document_type_combo.addItem(document_type["name"], document_type["id"])

        upload_form.addRow("Dokumenttyp:", self.document_type_combo)
        upload_form.addRow("Beschreibung:", self.document_description_input)

        self.file_list_widget = QListWidget()
        self.file_list_widget.setFixedHeight(120)

        upload_buttons = QHBoxLayout()
        self.choose_files_button = QPushButton("Dateien auswählen")
        self.choose_files_button.clicked.connect(self.on_select_files)
        self.clear_files_button = QPushButton("Auswahl löschen")
        self.clear_files_button.clicked.connect(self.on_clear_files)
        self.upload_files_button = QPushButton("Dokumente hochladen")
        self.upload_files_button.setObjectName("primaryButton")
        self.upload_files_button.clicked.connect(self.on_upload_files)
        upload_buttons.addWidget(self.choose_files_button)
        upload_buttons.addWidget(self.clear_files_button)
        upload_buttons.addWidget(self.upload_files_button)
        upload_buttons.addStretch()

        self.documents_table = TableWidget(7)
        self.documents_table.setHorizontalHeaderLabels([
            "Titel",
            "Typ",
            "Fall",
            "Hochgeladen",
            "Status",
            "Öffnen",
            "Löschen",
        ])
        self.documents_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.documents_table.setSelectionBehavior(self.documents_table.SelectionBehavior.SelectRows)
        self.documents_table.setEditTriggers(self.documents_table.EditTrigger.NoEditTriggers)

        document_layout.addLayout(upload_form)
        document_layout.addLayout(upload_buttons)
        document_layout.addWidget(self.file_list_widget)
        document_layout.addWidget(self.documents_table)
        document_card.setLayout(document_layout)

        action_layout = QHBoxLayout()
        action_layout.addStretch()
        self.print_button = QPushButton("Dossier drucken")
        self.print_button.setObjectName("primaryButton")
        self.print_button.clicked.connect(self.on_print_dossier)
        close_button = QPushButton("Schließen")
        close_button.clicked.connect(self.reject)
        action_layout.addWidget(self.print_button)
        action_layout.addWidget(close_button)

        main_layout.addWidget(header_box)
        main_layout.addWidget(person_box)
        main_layout.addWidget(claims_box)
        main_layout.addWidget(document_card)
        main_layout.addLayout(action_layout)
        self.setLayout(main_layout)

    def load_person(self) -> None:
        person = self.person_repository.get_person_by_id(self.person_id)
        if not person:
            QMessageBox.critical(self, "Person nicht gefunden", "Die gewünschte Person konnte nicht gefunden werden.")
            self.reject()
            return

        self.name_label.setText(f"{person.get('first_name','-')} {person.get('last_name','-')}")
        self.address_label.setText(person.get("address") or "-")
        self.city_label.setText(
            f"{person.get('postal_code','-')} {person.get('city','-')}" if person.get("postal_code") or person.get("city") else "-"
        )
        self.email_label.setText(person.get("email") or "-")
        self.birthdate_label.setText(person.get("birthdate") or "-")

    def load_claims(self) -> None:
        claims = self.claim_service.list_claims(person_id=self.person_id)
        if not claims:
            self.claims_label.setText("Keine verknüpften Fälle gefunden.")
            return

        lines = []
        for claim in claims:
            lines.append(
                f"{claim.get('case_number', '-')} – {claim.get('status', '-')} – {claim.get('category_name', '-') or '-'} – {claim.get('location_name', '-') or '-'}"
            )
        self.claims_label.setText("\n".join(lines))

    def refresh_documents(self) -> None:
        documents = self.document_service.list_documents(person_id=self.person_id)
        self.documents_table.setRowCount(0)

        for row_index, document in enumerate(documents):
            self.documents_table.insertRow(row_index)
            self.documents_table.setItem(row_index, 0, QTableWidgetItem(document.get("title", "-")))
            self.documents_table.setItem(row_index, 1, QTableWidgetItem(document.get("document_type_name", "-")))
            self.documents_table.setItem(row_index, 2, QTableWidgetItem(document.get("claim_case_number", "-")))
            self.documents_table.setItem(row_index, 3, QTableWidgetItem(document.get("uploaded_at", "-")))
            self.documents_table.setItem(row_index, 4, QTableWidgetItem(document.get("status", "-")))

            open_button = QPushButton("Öffnen")
            open_button.clicked.connect(lambda _, doc_id=document["id"]: self.open_document(doc_id))
            delete_button = QPushButton("Löschen")
            delete_button.clicked.connect(lambda _, doc_id=document["id"]: self.delete_document(doc_id))
            self.documents_table.setCellWidget(row_index, 5, open_button)
            self.documents_table.setCellWidget(row_index, 6, delete_button)

    def on_select_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Dokumente auswählen",
            str(Path.home()),
            "PDF-Dateien (*.pdf);;Alle Dateien (*)",
        )
        if files:
            self.selected_files = files
            self.file_list_widget.clear()
            for file_path in files:
                self.file_list_widget.addItem(file_path)

    def on_clear_files(self) -> None:
        self.selected_files = []
        self.file_list_widget.clear()

    def on_upload_files(self) -> None:
        if not self.selected_files:
            QMessageBox.warning(self, "Keine Dateien", "Bitte wählen Sie zuerst mindestens eine Datei aus.")
            return

        document_type_id = self.document_type_combo.currentData()
        if document_type_id is None:
            QMessageBox.warning(self, "Dokumenttyp fehlt", "Bitte wählen Sie einen Dokumenttyp aus.")
            return

        description = self.document_description_input.text().strip() or None
        errors: list[str] = []

        for file_path in self.selected_files:
            try:
                self.document_service.create_document(
                    source_file_path=file_path,
                    title=Path(file_path).stem,
                    document_type_id=document_type_id,
                    description=description,
                    person_id=self.person_id,
                )
            except Exception as exc:
                errors.append(f"{Path(file_path).name}: {exc}")

        self.on_clear_files()
        self.refresh_documents()

        if errors:
            QMessageBox.warning(
                self,
                "Einige Dokumente konnten nicht hochgeladen werden",
                "\n".join(errors),
            )
        else:
            QMessageBox.information(self, "Dokumente hochgeladen", "Die ausgewählten Dokumente wurden hochgeladen.")

    def open_document(self, document_id: int) -> None:
        try:
            path = self.document_service.get_document_path(document_id)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as exc:
            QMessageBox.warning(self, "Datei öffnen fehlgeschlagen", str(exc))

    def delete_document(self, document_id: int) -> None:
        if QMessageBox.question(
            self,
            "Dokument löschen",
            "Möchten Sie das Dokument wirklich aus dem Dossier entfernen?",
        ) != QMessageBox.StandardButton.Yes:
            return

        if self.document_service.delete_document(document_id):
            QMessageBox.information(self, "Dokument gelöscht", "Das Dokument wurde entfernt.")
            self.refresh_documents()
        else:
            QMessageBox.warning(self, "Löschen fehlgeschlagen", "Das Dokument konnte nicht gelöscht werden.")

    def on_print_dossier(self) -> None:
        try:
            pdf_path = self.pdf_service.generate_person_dossier_pdf(self.person_id)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf_path)))
            QMessageBox.information(self, "Dossier gedruckt", f"Dossier als PDF gespeichert unter:\n{pdf_path}")
        except Exception as exc:
            QMessageBox.warning(self, "Dossierdruck fehlgeschlagen", str(exc))
