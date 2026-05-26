from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QPushButton,
    QDialogButtonBox,
    QFileDialog,
    QMessageBox,
    QDateEdit,
    QCheckBox,
)

from services.document_service import DocumentService
from services.location_service import LocationService


class DocumentDialog(QDialog):
    def __init__(
        self,
        document_service: DocumentService,
        location_service: LocationService | None = None,
    ):
        super().__init__()
        self.document_service = document_service
        self.location_service = location_service or LocationService()
        self.selected_file: str | None = None
        self.setWindowTitle("Dokument hochladen")
        self.setup_ui()

    def setup_ui(self):
        self.setMinimumWidth(520)
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.file_label = QLabel("Keine Datei ausgewählt")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color: #4c4c4c;")

        choose_file_button = QPushButton("Datei wählen")
        choose_file_button.clicked.connect(self.choose_file)

        self.title_input = QLineEdit()
        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(80)

        self.document_type_input = QComboBox()
        for document_type in self.document_service.list_document_types():
            self.document_type_input.addItem(document_type["name"], document_type["id"])

        self.claim_id_input = QLineEdit()
        self.person_id_input = QLineEdit()
        self.card_id_input = QLineEdit()
        self.location_input = QComboBox()
        self.location_input.addItem("Kein Standort", None)
        for location in self.location_service.list_active_locations():
            self.location_input.addItem(location["name"], location["id"])

        self.expiry_date_check = QCheckBox("Ablaufdatum setzen")
        self.expiry_date_check.stateChanged.connect(self._toggle_expiry)
        self.expiry_date_edit = QDateEdit()
        self.expiry_date_edit.setCalendarPopup(True)
        self.expiry_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.expiry_date_edit.setDate(QDate.currentDate().addYears(1))
        self.expiry_date_edit.setEnabled(False)

        form_layout.addRow("Datei:", self.file_label)
        form_layout.addRow("", choose_file_button)
        form_layout.addRow("Titel:", self.title_input)
        form_layout.addRow("Dokumenttyp:", self.document_type_input)
        form_layout.addRow("Fall-ID:", self.claim_id_input)
        form_layout.addRow("Personen-ID:", self.person_id_input)
        form_layout.addRow("Karten-ID:", self.card_id_input)
        form_layout.addRow("Standort:", self.location_input)
        form_layout.addRow("Ablaufdatum:", self.expiry_date_check)
        form_layout.addRow("", self.expiry_date_edit)
        form_layout.addRow("Beschreibung:", self.description_input)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _toggle_expiry(self, state: int) -> None:
        self.expiry_date_edit.setEnabled(bool(state))

    def choose_file(self):
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "Dokument auswählen",
            "",
            "Alle Dateien (*.*)",
        )
        if not selected_file:
            return
        self.selected_file = selected_file
        self.file_label.setText(selected_file)

    def accept(self) -> None:
        if not self.selected_file:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie eine Datei aus.")
            return

        if self.document_type_input.currentData() is None:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie einen Dokumenttyp.")
            return

        if not self.title_input.text().strip():
            self.title_input.setText(self.file_label.text())

        super().accept()

    def get_data(self) -> dict:
        location_id = self.location_input.currentData()
        return {
            "source_file_path": self.selected_file or "",
            "title": self.title_input.text().strip() or "",
            "document_type_id": self.document_type_input.currentData(),
            "description": self.description_input.toPlainText().strip() or None,
            "claim_id": int(self.claim_id_input.text().strip()) if self.claim_id_input.text().strip().isdigit() else None,
            "person_id": int(self.person_id_input.text().strip()) if self.person_id_input.text().strip().isdigit() else None,
            "card_id": int(self.card_id_input.text().strip()) if self.card_id_input.text().strip().isdigit() else None,
            "location_id": location_id,
        }
