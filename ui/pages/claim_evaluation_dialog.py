from typing import Dict

from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QComboBox,
    QPushButton,
    QGroupBox,
    QMessageBox,
    QDialogButtonBox,
    QCheckBox,
    QScrollArea,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from pathlib import Path

from core.session import Session
from services.claim_service import ClaimService
from services.document_service import DocumentService
from services.pdf_service import PDFService


class ClaimEvaluationDialog(QDialog):
    def __init__(self, claim_id: int | None = None, claim_service: ClaimService | None = None):
        super().__init__()
        self.claim_id = claim_id
        self.claim_service = claim_service or ClaimService()
        self.current_evaluation = None
        self.claim = None

        self.setWindowTitle("Anspruchsprüfung")
        self.setMinimumWidth(1000)
        # make dialog a top-level window with minimize/maximize buttons
        flags = self.windowFlags()
        flags |= Qt.WindowType.Window
        flags |= Qt.WindowType.WindowMinimizeButtonHint
        flags |= Qt.WindowType.WindowMaximizeButtonHint
        self.setWindowFlags(flags)

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        header_card = QGroupBox()
        header_card.setTitle("")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(16)

        title = QLabel("Anspruchsprüfung")
        title.setObjectName("pageTitle")

        self.meta_label = QLabel("")
        self.meta_label.setWordWrap(True)
        self.meta_label.setStyleSheet("color: #52606d;")

        header_texts = QVBoxLayout()
        header_texts.addWidget(title)
        header_texts.addWidget(self.meta_label)
        header_texts.addStretch()

        header_layout.addLayout(header_texts)
        header_card.setLayout(header_layout)
        main_layout.addWidget(header_card)

        self.income_fields: dict[str, QLineEdit] = {}
        income_names = [
            "Gehalt",
            "Pension",
            "Invalidenrente",
            "AMS-Bezüge",
            "Krankengeld",
            "Kinderbetreuungsgeld",
            "Wohnbeihilfe",
            "Alimente",
            "Mindestsicherung",
            "Unterhaltszahlungen",
            "Diverse andere Einkommen",
            "Vermoegen",
            "Schenkungen",
        ]
        for name in income_names:
            le = QLineEdit("0")
            le.setPlaceholderText(name)
            self.income_fields[name] = le

        self.expense_fields: dict[str, tuple[QLineEdit, QCheckBox, QLineEdit]] = {}
        expense_names = [
            "Miete",
            "Betriebskosten",
            "Stromkosten",
            "Kinderbetreuung",
            "Kindergarten",
            "Pflegeaufwand",
            "Unterhaltszahlungen (Inland)",
            "Lohnpfändung",
            "Haushaltsversicherung",
            "Gebäudeversicherung",
            "Medikamente",
            "Autoversicherung",
            "Handy-Abo",
        ]
        for name in expense_names:
            amount = QLineEdit("0")
            amount.setPlaceholderText("Betrag")
            proof = QCheckBox("Nachweis")
            note = QLineEdit()
            note.setPlaceholderText("Bemerkung")
            self.expense_fields[name] = (amount, proof, note)

        self.adult_count_input = QSpinBox()
        self.adult_count_input.setMinimum(1)
        self.adult_count_input.setMaximum(10)
        self.adult_count_input.setValue(1)

        self.child_count_input = QSpinBox()
        self.child_count_input.setMinimum(0)
        self.child_count_input.setMaximum(10)
        self.child_count_input.setValue(0)

        self.category_combo = QComboBox()
        self._fill_categories()
        self.category_combo.currentTextChanged.connect(self._on_category_changed)

        self.disability_degree_input = QSpinBox()
        self.disability_degree_input.setMinimum(0)
        self.disability_degree_input.setMaximum(100)
        self.disability_degree_input.setValue(0)
        self.disability_degree_input.setEnabled(False)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(18)

        # Left column: Einnahmen und Haushaltsdaten
        left_col = QVBoxLayout()
        income_box = QGroupBox("Einnahmen")
        income_layout = QGridLayout()
        income_layout.setHorizontalSpacing(16)
        income_layout.setVerticalSpacing(12)
        for row, (name, widget) in enumerate(self.income_fields.items()):
            label = QLabel(name)
            income_layout.addWidget(label, row, 0)
            income_layout.addWidget(widget, row, 1)
        income_box.setLayout(income_layout)

        household_box = QGroupBox("Haushaltsdaten")
        household_form = QFormLayout()
        household_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        household_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        household_form.setHorizontalSpacing(20)
        household_form.setVerticalSpacing(10)
        household_form.addRow("Erwachsene Personen", self.adult_count_input)
        household_form.addRow("Kinder", self.child_count_input)
        household_form.addRow("Kategorie", self.category_combo)
        household_form.addRow("Behinderungsgrad (%)", self.disability_degree_input)
        household_box.setLayout(household_form)

        left_col.addWidget(income_box)
        left_col.addWidget(household_box)

        # Middle column: Ausgaben
        expense_box = QGroupBox("Ausgaben")
        expense_grid = QGridLayout()
        expense_grid.setHorizontalSpacing(16)
        expense_grid.setVerticalSpacing(12)
        for row, (name, fields) in enumerate(self.expense_fields.items(), start=0):
            amount, proof, note = fields
            expense_grid.addWidget(QLabel(name), row, 0)
            expense_grid.addWidget(amount, row, 1)
            expense_grid.addWidget(proof, row, 2)
            expense_grid.addWidget(note, row, 3)
        expense_box.setLayout(expense_grid)

        middle_col = QVBoxLayout()
        middle_col.addWidget(expense_box)

        # Right column: Ergebnis
        result_box = QGroupBox("Prüfungsergebnis")
        result_layout = QVBoxLayout()
        result_layout.setSpacing(12)

        self.status_label = QLabel("Bitte Eingaben prüfen und auf Prüfung klicken.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #52606d;")

        self.result_status = QLabel("-")
        self.result_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_status.setWordWrap(True)
        self.result_status.setMinimumHeight(100)
        self.result_status.setStyleSheet(
            "font-size: 22px; font-weight: 700; border-radius: 12px; padding: 18px;"
        )

        self.result_reason = QLabel("-")
        self.result_reason.setWordWrap(True)
        self.result_reason.setStyleSheet("color: #52606d;")

        self.result_totals = QLabel("-")
        self.result_totals.setWordWrap(True)
        self.result_details = QLabel("-")
        self.result_details.setWordWrap(True)

        result_layout.addWidget(self.result_status)
        result_layout.addSpacing(12)
        result_layout.addWidget(QLabel("Begründung"))
        result_layout.addWidget(self.result_reason)
        result_layout.addSpacing(8)
        result_layout.addWidget(QLabel("Berechnete Werte"))
        result_layout.addWidget(self.result_totals)
        result_layout.addWidget(self.result_details)
        result_box.setLayout(result_layout)
        result_box.setMinimumWidth(260)

        right_col = QVBoxLayout()
        right_col.addWidget(result_box)
        right_col.addStretch()

        body_layout.addLayout(left_col, 10)
        body_layout.addLayout(middle_col, 14)
        body_layout.addLayout(right_col, 9)

        main_layout.addLayout(body_layout)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.start_button = QPushButton("Prüfung starten")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.evaluate_claim)

        self.apply_status_button = QPushButton("Prüfung abschließen")
        self.apply_status_button.setObjectName("secondaryButton")
        self.apply_status_button.setEnabled(False)
        self.apply_status_button.clicked.connect(self.apply_status)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.apply_status_button)
        button_layout.addStretch()
        button_layout.addWidget(buttons)

        main_layout.addLayout(button_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_widget.setLayout(main_layout)
        scroll_area.setWidget(content_widget)

        outer_layout = QVBoxLayout()
        outer_layout.addWidget(scroll_area)
        self.setLayout(outer_layout)

        if self.claim_id:
            self.load_claim()

    def _fill_categories(self) -> None:
        categories = self.claim_service.get_valid_categories()
        self.category_combo.clear()
        for category in categories:
            self.category_combo.addItem(category)

    def _on_category_changed(self, category: str) -> None:
        self.disability_degree_input.setEnabled(category == "Menschen mit Beeinträchtigung")

    def _parse_float(self, value: QLineEdit) -> float:
        try:
            return max(float(value.text().strip() or 0), 0.0)
        except ValueError:
            return 0.0

    def evaluate_claim(self) -> None:
        incomes = {k: self._parse_float(v) for k, v in self.income_fields.items()}
        expenses = {k: float(amount.text().strip() or 0) for k, (amount, _, _) in self.expense_fields.items()}

        category = self.category_combo.currentText()
        disability_degree = (
            self.disability_degree_input.value()
            if category == "Menschen mit Beeinträchtigung"
            else None
        )

        evaluation = self.claim_service.evaluate_claim(
            incomes=incomes,
            expenses=expenses,
            adult_count=self.adult_count_input.value(),
            child_count=self.child_count_input.value(),
            category=category,
            disability_degree=disability_degree,
        )

        self.current_evaluation = evaluation
        status_text = evaluation["status"]
        status_icon = "●"
        self.result_status.setText(f"{status_icon} {status_text}")
        self.result_reason.setText(evaluation["reason"])
        self.result_totals.setText(
            f"Einnahmen: {evaluation['total_income']:.2f} €\n"
            f"Ausgaben: {evaluation['total_expenses']:.2f} €\n"
            f"Frei verfügbar: {evaluation['free_income']:.2f} €"
        )
        self.result_details.setText(
            f"Anspruchsgrenze: {evaluation['entitlement_limit']:.2f} €\n"
            f"Härtefallgrenze: {evaluation['hardship_limit']:.2f} €"
        )

        if status_text == "ANSPRUCHSBERECHTIGT":
            self.result_status.setStyleSheet(
                "font-size: 22px; font-weight: 700; border-radius: 12px; padding: 18px;"
                "background-color: #e7f7ef; color: #1f7a5a; border: 1px solid #b7e4cf;"
            )
        elif status_text == "HAERTEFALL":
            self.result_status.setStyleSheet(
                "font-size: 22px; font-weight: 700; border-radius: 12px; padding: 18px;"
                "background-color: #fff7e6; color: #9a6700; border: 1px solid #f7d9a3;"
            )
        else:
            self.result_status.setStyleSheet(
                "font-size: 22px; font-weight: 700; border-radius: 12px; padding: 18px;"
                "background-color: #fdecec; color: #b42318; border: 1px solid #f5c2c0;"
            )

        self.status_label.setText("Auswertung abgeschlossen. Status kann übernommen werden.")
        self.apply_status_button.setEnabled(True)

    def _apply_status_style(self, status: str) -> None:
        if status == "ANSPRUCHSBERECHTIGT":
            self.result_status.setStyleSheet(
                "font-size: 22px; font-weight: 700; border-radius: 12px; padding: 18px;"
                "background-color: #e7f7ef; color: #1f7a5a; border: 1px solid #b7e4cf;"
            )
        elif status == "HAERTEFALL":
            self.result_status.setStyleSheet(
                "font-size: 22px; font-weight: 700; border-radius: 12px; padding: 18px;"
                "background-color: #fff7e6; color: #9a6700; border: 1px solid #f7d9a3;"
            )
        else:
            self.result_status.setStyleSheet(
                "font-size: 22px; font-weight: 700; border-radius: 12px; padding: 18px;"
                "background-color: #fdecec; color: #b42318; border: 1px solid #f5c2c0;"
            )

    def apply_status(self) -> None:
        if self.current_evaluation is None:
            QMessageBox.warning(self, "Keine Auswertung", "Bitte führen Sie zuerst eine Auswertung durch.")
            return

        if self.claim_id is None:
            QMessageBox.information(
                self,
                "Auswertung abgeschlossen",
                "Die Prüfung wurde durchgeführt, aber kein Anspruch zum Aktualisieren ist zugeordnet.",
            )
            return

        # collect incomes and expenses with details to persist
        incomes = {k: self._parse_float(v) for k, v in self.income_fields.items()}
        expenses = {}
        for k, (amount, proof, note) in self.expense_fields.items():
            expenses[k] = {"amount": self._parse_float(amount), "has_proof": proof.isChecked(), "note": note.text().strip()}

        category = self.category_combo.currentText()
        disability_degree = (
            self.disability_degree_input.value()
            if category == "Menschen mit Beeinträchtigung"
            else None
        )

        if not category:
            QMessageBox.warning(self, "Ungültige Kategorie", "Bitte wählen Sie eine Kategorie für die Prüfung aus.")
            return

        try:
            evaluation = self.claim_service.persist_evaluation(
                claim_id=self.claim_id,
                incomes=incomes,
                expenses=expenses,
                adult_count=self.adult_count_input.value(),
                child_count=self.child_count_input.value(),
                category=category,
                disability_degree=disability_degree,
                examiner_id=Session.get_user_id(),
            )

            pdf_service = PDFService()
            pdf_path = pdf_service.generate_claim_evaluation_pdf(self.claim_id)
            document_service = DocumentService()
            document_types = document_service.list_document_types()
            pruefprotokoll = next((dt for dt in document_types if dt["name"] == "Prüfprotokoll"), None)
            if pruefprotokoll is not None:
                document_service.create_document(
                    source_file_path=pdf_path,
                    title="Prüfungsprotokoll",
                    document_type_id=pruefprotokoll["id"],
                    description="Automatisch generiertes Prüfungsprotokoll",
                    claim_id=self.claim_id,
                    person_id=self.claim.get("person_id") if self.claim else None,
                    location_id=self.claim.get("location_id") if self.claim else None,
                )
                # offer to open the created PDF for the user
                try:
                    if Path(pdf_path).exists():
                        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf_path)))
                except Exception:
                    # fall back to a simple success dialog offering open actions
                    pass
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern der Daten: {e}")
            return

        QMessageBox.information(self, "Status aktualisiert", f"Der Anspruchsstatus wurde auf '{evaluation['status']}' gesetzt.")
        self.accept()

    def _offer_open_pdf(self, pdf_path: str) -> None:
        """Zeigt nach erfolgreicher PDF-Erzeugung einen Dialog mit Öffnen/Ordner-Öffnen-Optionen."""
        try:
            msg = QMessageBox(self)
            msg.setWindowTitle("PDF erzeugt")
            msg.setText(f"PDF gespeichert unter:\n{pdf_path}")
            open_btn = msg.addButton("Öffnen", QMessageBox.ButtonRole.AcceptRole)
            open_folder_btn = msg.addButton("Ordner öffnen", QMessageBox.ButtonRole.ActionRole)
            msg.addButton(QMessageBox.StandardButton.Close)
            msg.exec()
            clicked = msg.clickedButton()
            if clicked == open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf_path)))
            elif clicked == open_folder_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(pdf_path).parent)))
        except Exception:
            return

    def load_claim(self) -> None:
        claim = self.claim_service.get_claim_by_id(self.claim_id)
        if not claim:
            return
        self.claim = claim
        meta = (
            f"Fall: {claim.get('case_number', '-')}, Person: {claim.get('person_first_name','') or ''} {claim.get('person_last_name','') or ''}, "
            f"Standort: {claim.get('location_name','-')}, Kategorie: {claim.get('category_name','-')}, Status: {claim.get('status','-')}"
        )
        self.meta_label.setText(meta)

        self.adult_count_input.setValue(claim.get("adult_count") or 1)
        self.child_count_input.setValue(claim.get("child_count") or 0)
        self.disability_degree_input.setValue(claim.get("disability_degree") or 0)

        category_name = claim.get("category_name")
        if category_name:
            index = self.category_combo.findText(category_name)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)

        self._on_category_changed(self.category_combo.currentText())

        incomes = {item["type"]: item["amount"] for item in claim.get("incomes", [])}
        for name, widget in self.income_fields.items():
            widget.setText(f"{incomes.get(name, 0.0):.2f}")

        expenses = {item["type"]: item for item in claim.get("expenses", [])}
        for name, (amount, proof, note) in self.expense_fields.items():
            row = expenses.get(name)
            amount.setText(f"{row['amount']:.2f}" if row else "0.00")
            proof.setChecked(bool(row and row.get("has_proof")))
            note.setText(row.get("note", "") if row else "")

        if claim.get("status") and claim.get("evaluation_reason") is not None:
            self.result_status.setText(f"● {claim['status']}")
            self.result_reason.setText(claim.get("evaluation_reason") or "-")
            self.result_totals.setText(
                f"Einnahmen: {claim.get('total_income', 0.0):.2f} €\n"
                f"Ausgaben: {claim.get('total_expenses', 0.0):.2f} €\n"
                f"Frei verfügbar: {claim.get('free_income', 0.0):.2f} €"
            )
            self.result_details.setText(
                f"Anspruchsgrenze: {claim.get('entitlement_limit', 0.0):.2f} €\n"
                f"Härtefallgrenze: {claim.get('hardship_limit', 0.0):.2f} €"
            )
            self._apply_status_style(claim['status'])
            self.status_label.setText("Vorhandene Prüfung geladen. Bitte neu auswerten, wenn Änderungen nötig sind.")
        else:
            self.status_label.setText("Bitte Eingaben prüfen und auf Prüfung klicken.")
