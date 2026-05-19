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
)
from PyQt6.QtCore import Qt

from services.case_service import CaseService
from services.claim_service import ClaimService
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
        self.setMinimumWidth(720)

        self.case_service = case_service or CaseService()
        self.claim_service = claim_service or ClaimService()

        self.created_case = None

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

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

        main_layout.addWidget(header_card)

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
        main_layout.addWidget(person_card)

        case_card = QGroupBox("Fallinformation")
        case_layout = QVBoxLayout()
        case_layout.setSpacing(12)
        self.case_number_label = QLabel("Fallnummer wird nach dem Speichern angezeigt.")
        case_number_text = QLabel("Fallnummer")
        case_number_text.setStyleSheet("font-weight: 600; color: #52606d;")
        case_layout.addWidget(case_number_text)
        case_layout.addWidget(self.case_number_label)
        case_card.setLayout(case_layout)
        main_layout.addWidget(case_card)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.save_button = QPushButton("Speichern und Fall anlegen")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self.on_save)

        self.start_eval_button = QPushButton("Prüfung starten")
        self.start_eval_button.setObjectName("primaryButton")
        self.start_eval_button.setEnabled(False)
        self.start_eval_button.clicked.connect(self.on_start_evaluation)

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.start_eval_button)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)
        self.load_choices()

    def load_choices(self):
        self.category_combo.clear()
        for c in self.case_service.list_categories():
            self.category_combo.addItem(c["name"], c["id"])

        self.location_combo.clear()
        for l in self.case_service.list_locations():
            self.location_combo.addItem(l["name"], l["id"])

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
        QMessageBox.information(self, "Erfolg", "Person und Fall wurden angelegt.")

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
