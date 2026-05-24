from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QLabel,
    QMessageBox,
    QGroupBox,
    QWidget,
    QFileDialog,
    QListWidget,
    QScrollArea,
)
from PyQt6.QtCore import Qt

from services.case_service import CaseService
from services.claim_service import ClaimService
from services.document_service import DocumentService
from ui.pages.claim_evaluation_dialog import ClaimEvaluationDialog


class CaseCreateDialog(QDialog):
    def __init__(
        self,
        parent=None,
        case_service: CaseService | None = None,
        claim_service: ClaimService | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Neuen Antrag / Person erfassen")
        # Make this dialog a proper top-level window with minimize/maximize
        flags = self.windowFlags()
        flags |= Qt.WindowType.Window
        flags |= Qt.WindowType.WindowMinimizeButtonHint
        flags |= Qt.WindowType.WindowMaximizeButtonHint
        self.setWindowFlags(flags)
        # Allow resizing and sensible default size
        self.setMinimumSize(720, 480)
        self.resize(900, 700)

        self.case_service = case_service or CaseService()
        self.claim_service = claim_service or ClaimService()
        self.document_service = DocumentService()

        self.created_case = None
        self.selected_files: list[str] = []

        self.setup_ui()

    def setup_ui(self):
        # Main content layout placed inside a scrollable area
        content_layout = QVBoxLayout()
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Neue Person und neuer Fall")
        header.setObjectName("pageTitle")
        description = QLabel("Personendaten erfassen, Kategorie und Standort wählen, Fallnummer generieren und Prüfung starten.")
        description.setWordWrap(True)
        description.setObjectName("sectionDescription")

        header_card = QWidget()
        header_card.setObjectName("cardContainer")
        header_card_layout = QVBoxLayout(header_card)
        header_card_layout.setContentsMargins(18, 16, 18, 16)
        header_card_layout.setSpacing(6)
        header_card_layout.addWidget(header)
        header_card_layout.addWidget(description)

        content_layout.addWidget(header_card)

        person_card = QGroupBox("Personendaten")
        person_form = QFormLayout()
        person_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        person_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        person_form.setHorizontalSpacing(20)
        person_form.setVerticalSpacing(12)

        self.last_name = QLineEdit()
        self.first_name = QLineEdit()
        self.address = QLineEdit()
        self.postal_code = QLineEdit()
        self.city = QLineEdit()
        self.email = QLineEdit()
        self.category_combo = QComboBox()
        self.location_combo = QComboBox()

        person_form.addRow("Name", self.last_name)
        person_form.addRow("Vorname", self.first_name)
        person_form.addRow("Adresse", self.address)
        person_form.addRow("PLZ", self.postal_code)
        person_form.addRow("Ort", self.city)
        person_form.addRow("E-Mail-Adresse", self.email)
        person_form.addRow("Kategorie", self.category_combo)
        person_form.addRow("Standort", self.location_combo)

        person_card.setLayout(person_form)
        content_layout.addWidget(person_card)

        case_card = QGroupBox("Fallinformation")
        case_layout = QVBoxLayout()
        case_layout.setSpacing(12)
        self.case_number_label = QLabel("Fallnummer wird nach dem Speichern angezeigt.")
        case_number_text = QLabel("Fallnummer")
        case_number_text.setStyleSheet("font-weight: 600; color: #52606d;")
        case_layout.addWidget(case_number_text)
        case_layout.addWidget(self.case_number_label)
        case_card.setLayout(case_layout)
        content_layout.addWidget(case_card)

        document_card = QGroupBox("Dokumente zum Antrag")
        document_layout = QVBoxLayout()
        document_layout.setSpacing(12)

        self.document_type_combo = QComboBox()
        self.document_description = QLineEdit()
        self.document_description.setPlaceholderText("Optionale Beschreibung")
        self.selected_files_list = QListWidget()
        self.selected_files_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.selected_files_list.setFixedHeight(120)

        file_button_row = QHBoxLayout()
        self.select_files_button = QPushButton("Dateien auswählen")
        self.select_files_button.clicked.connect(self.on_select_files)
        self.clear_files_button = QPushButton("Auswahl löschen")
        self.clear_files_button.clicked.connect(self.on_clear_files)
        file_button_row.addWidget(self.select_files_button)
        file_button_row.addWidget(self.clear_files_button)
        file_button_row.addStretch()

        document_form = QFormLayout()
        document_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        document_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        document_form.setHorizontalSpacing(20)
        document_form.setVerticalSpacing(10)
        document_form.addRow("Dokumenttyp", self.document_type_combo)
        document_form.addRow("Beschreibung", self.document_description)

        document_layout.addLayout(document_form)
        document_layout.addLayout(file_button_row)
        document_layout.addWidget(self.selected_files_list)
        document_card.setLayout(document_layout)
        content_layout.addWidget(document_card)

        # Action buttons are placed outside the scroll area so they remain reachable
        self.save_button = QPushButton("Speichern und Fall anlegen")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self.on_save)

        self.start_eval_button = QPushButton("Prüfung starten")
        self.start_eval_button.setObjectName("primaryButton")
        self.start_eval_button.setEnabled(False)
        self.start_eval_button.clicked.connect(self.on_start_evaluation)

        action_bar = QWidget()
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(12, 8, 12, 12)
        action_layout.setSpacing(12)
        action_layout.addWidget(self.save_button)
        action_layout.addWidget(self.start_eval_button)
        action_layout.addStretch()

        # Scroll area for content
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)
        outer_layout.addWidget(action_bar)

        self.setLayout(outer_layout)
        self.load_choices()
        self.load_document_types()

    def _upload_documents(self, created_case: dict[str, object]) -> None:
        if not created_case:
            return

        claim_id = created_case.get("id")
        person_id = created_case.get("person_id")
        location_id = self.location_combo.currentData()
        document_type_id = self.document_type_combo.currentData()
        description = self.document_description.text().strip() or None

        for file_path in self.selected_files:
            try:
                self.document_service.create_document(
                    source_file_path=file_path,
                    title=Path(file_path).stem,
                    document_type_id=document_type_id,
                    description=description,
                    claim_id=claim_id,
                    person_id=person_id,
                    location_id=location_id,
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Dokument hochladen fehlgeschlagen",
                    f"Datei '{Path(file_path).name}' konnte nicht hochgeladen werden: {e}",
                )

        self.load_document_types()

    def load_choices(self):
        self.category_combo.clear()
        for c in self.case_service.list_categories():
            self.category_combo.addItem(c["name"], c["id"])

        self.location_combo.clear()
        for l in self.case_service.list_locations():
            self.location_combo.addItem(l["name"], l["id"])

    def load_document_types(self):
        self.document_type_combo.clear()
        doc_types = self.document_service.list_document_types()
        if not doc_types:
            self.document_type_combo.addItem("Keine Dokumenttypen verfügbar", None)
            return

        for document_type in doc_types:
            self.document_type_combo.addItem(document_type["name"], document_type["id"])
        self.document_type_combo.setCurrentIndex(0)

    def on_select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Dokumente zum Antrag auswählen",
            str(Path.home()),
            "PDF-Dateien (*.pdf);;Alle Dateien (*)",
        )
        if files:
            self.selected_files = files
            self.selected_files_list.clear()
            for file_path in files:
                self.selected_files_list.addItem(file_path)

    def on_clear_files(self):
        self.selected_files = []
        self.selected_files_list.clear()

    def on_save(self):
        # validate required fields
        required = [
            (self.last_name, "Name"),
            (self.first_name, "Vorname"),
            (self.address, "Adresse"),
            (self.postal_code, "PLZ"),
            (self.city, "Ort"),
            (self.email, "E-Mail"),
        ]

        for widget, label in required:
            if not widget.text().strip():
                QMessageBox.warning(self, "Pflichtfeld fehlt", f"Bitte '{label}' ausfüllen.")
                return

        person = {
            "first_name": self.first_name.text().strip(),
            "last_name": self.last_name.text().strip(),
            "address": self.address.text().strip(),
            "postal_code": self.postal_code.text().strip(),
            "city": self.city.text().strip(),
            "email": self.email.text().strip(),
            "category_id": self.category_combo.currentData(),
            "location_id": self.location_combo.currentData(),
        }

        try:
            result = self.case_service.create_case(
                person=person,
                category_id=person.get("category_id"),
                location_id=person.get("location_id"),
                description="Anlage via Erfassungsmaske",
                created_by=self._get_current_user_id(),
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fall konnte nicht angelegt werden: {e}")
            return

        self.created_case = result
        self.case_number_label.setText(f"Fallnummer: {result['case_number']}")
        self.start_eval_button.setEnabled(True)

        if self.selected_files:
            self._upload_documents(result)

        QMessageBox.information(self, "Erfolg", "Person, Fall und ggf. Dokumente wurden angelegt.")

    def _get_current_user_id(self) -> int | None:
        from core.session import Session

        return Session.get_user_id()

    def on_start_evaluation(self):
        if not self.created_case:
            QMessageBox.warning(self, "Kein Fall", "Bitte zuerst einen Fall anlegen.")
            return

        claim_id = self.created_case.get("id")
        dlg = ClaimEvaluationDialog(claim_id=claim_id, claim_service=self.claim_service)
        dlg.exec()
