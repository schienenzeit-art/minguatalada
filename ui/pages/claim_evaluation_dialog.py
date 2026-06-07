import json
from datetime import datetime
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
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from pathlib import Path

from core.claim_status import ClaimStatus
from core.session import Session
from services.claim_service import ClaimService
from services.checklist_service import ChecklistService
from services.re_evaluation_service import ReEvaluationService
from services.document_service import DocumentService
from services.pdf_service import PDFService


class ClaimEvaluationDialog(QDialog):
    def __init__(
        self,
        claim_id: int | None = None,
        claim_service: ClaimService | None = None,
        checklist_service: ChecklistService | None = None,
        re_evaluation_service: ReEvaluationService | None = None,
    ):
        super().__init__()
        self.claim_id = claim_id
        self.claim_service = claim_service or ClaimService()
        self.checklist_service = checklist_service or ChecklistService()
        self.re_evaluation_service = re_evaluation_service or ReEvaluationService()
        self.current_evaluation = None
        self.claim = None
        self._lock_state: dict = {"locked": False}
        # Datenverlust-Schutz: True sobald eine Prüfung gestartet wurde,
        # False sobald die Prüfung gespeichert (apply_status) wurde.
        self._evaluation_started = False
        self._saved = False

        self.setWindowTitle("Anspruchsprüfung")
        self.setMinimumWidth(1000)
        # make dialog a top-level window with minimize/maximize buttons
        flags = self.windowFlags()
        flags |= Qt.WindowType.Window
        flags |= Qt.WindowType.WindowMinimizeButtonHint
        flags |= Qt.WindowType.WindowMaximizeButtonHint
        self.setWindowFlags(flags)

        self._autosave_timer: QTimer | None = None
        self.setup_ui()
        self._init_autosave()

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
            "Sonstige Einnahmen",
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
            "GIS/ORF Gebühr",
            "Sonstige Ausgaben 1",
            "Sonstige Ausgaben 2",
            "Sonstige Ausgaben 3",
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

        # Wohnbeihilfe-Checkbox (Anforderung 2) — direkt bei den Einnahmen
        self.housing_benefit_check = QCheckBox("Wohnbeihilfe vorhanden / beantragt")
        self.housing_benefit_check.setToolTip(
            "Bitte angeben ob die Person Wohnbeihilfe erhält oder beantragt hat.\n"
            "Fehlt die Wohnbeihilfe, wird der Fall vorläufig abgelehnt und eine weitere Abklärung ausgelöst."
        )
        self.housing_benefit_set = False  # Wird True sobald Nutzer explizit setzt

        # Wohnbeihilfe-Warnfeld — ebenfalls bei den Einnahmen
        self.housing_benefit_warning = QLabel(
            "Achtung: Keine Wohnbeihilfe angegeben → vorläufige Ablehnung + weitere Abklärung."
        )
        self.housing_benefit_warning.setStyleSheet(
            "color: #9a6700; background: #fff7e6; border: 1px solid #f7d9a3; "
            "border-radius: 6px; padding: 6px 10px;"
        )
        self.housing_benefit_warning.setWordWrap(True)
        self.housing_benefit_warning.setVisible(False)
        self.housing_benefit_check.toggled.connect(self._on_housing_benefit_changed)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(18)

        # Left column: Einnahmen und Haushaltsdaten
        left_col = QVBoxLayout()
        income_box = QGroupBox("Einnahmen")
        income_layout = QGridLayout()
        income_layout.setHorizontalSpacing(16)
        income_layout.setVerticalSpacing(12)
        grid_row = 0
        for name, widget in self.income_fields.items():
            label = QLabel(name)
            income_layout.addWidget(label, grid_row, 0)
            income_layout.addWidget(widget, grid_row, 1)
            grid_row += 1
            if name == "Wohnbeihilfe":
                income_layout.addWidget(self.housing_benefit_check, grid_row, 0, 1, 2)
                grid_row += 1
                income_layout.addWidget(self.housing_benefit_warning, grid_row, 0, 1, 2)
                grid_row += 1
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

        # ── Unterlagen-Checkliste (automatisch eingeblendet) ──────────────────
        checklist_box = QGroupBox("Unterlagen-Checkliste")
        checklist_layout = QVBoxLayout()
        checklist_layout.setContentsMargins(8, 8, 8, 8)
        self._checklist_placeholder = QLabel("Checkliste wird nach Öffnen eines Falls geladen.")
        self._checklist_placeholder.setStyleSheet("color: #9b9896; font-size: 11px;")
        self._checklist_placeholder.setWordWrap(True)
        checklist_layout.addWidget(self._checklist_placeholder)
        self._checklist_widget = None
        checklist_box.setLayout(checklist_layout)
        self._checklist_box = checklist_box
        self._checklist_inner_layout = checklist_layout

        right_col = QVBoxLayout()
        right_col.addWidget(result_box)
        right_col.addWidget(checklist_box)
        right_col.addStretch()

        body_layout.addLayout(left_col, 10)
        body_layout.addLayout(middle_col, 14)
        body_layout.addLayout(right_col, 9)

        main_layout.addLayout(body_layout)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        # ── Lock-Banner (sichtbar wenn Erstprüfung erfolgt und Mitarbeiter-Rolle) ─
        self._lock_banner = QLabel("")
        self._lock_banner.setWordWrap(True)
        self._lock_banner.setVisible(False)
        self._lock_banner.setStyleSheet(
            "color: #9a6700; background: #fff7e6; border: 1px solid #f7d9a3; "
            "border-radius: 6px; padding: 8px 12px; font-size: 12px;"
        )

        self.start_button = QPushButton("Prüfung starten")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.evaluate_claim)

        self.apply_status_button = QPushButton("Prüfung abschließen")
        self.apply_status_button.setObjectName("secondaryButton")
        self.apply_status_button.setEnabled(False)
        self.apply_status_button.clicked.connect(self.apply_status)

        self._request_approval_button = QPushButton("Freigabe anfordern …")
        self._request_approval_button.setObjectName("secondaryButton")
        self._request_approval_button.setVisible(False)
        self._request_approval_button.setToolTip(
            "Freigabe zur erneuten Prüfung beim Supervisor anfordern"
        )
        self._request_approval_button.clicked.connect(self._on_request_re_evaluation)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        button_layout.addWidget(self._lock_banner)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.apply_status_button)
        button_layout.addWidget(self._request_approval_button)
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
        # Behinderungsgrad: nur bei dieser Kategorie sichtbar (kein Mindestprozent mehr)
        self.disability_degree_input.setEnabled(category == "Menschen mit Beeinträchtigung")

    def _on_housing_benefit_changed(self, checked: bool) -> None:
        self.housing_benefit_set = True
        self.housing_benefit_warning.setVisible(not checked)

    def _parse_float(self, value: QLineEdit) -> float:
        try:
            return max(float(value.text().strip() or 0), 0.0)
        except ValueError:
            return 0.0

    def _get_has_housing_benefit(self) -> bool | None:
        if not self.housing_benefit_set:
            return None
        return self.housing_benefit_check.isChecked()

    def evaluate_claim(self) -> None:
        # Ab jetzt gilt die Prüfung als gestartet → Schließen wird abgesichert.
        self._evaluation_started = True
        try:
            incomes = {k: self._parse_float(v) for k, v in self.income_fields.items()}
            expenses = {k: float(amount.text().strip() or 0) for k, (amount, _, _) in self.expense_fields.items()}

            category = self.category_combo.currentText()
            disability_degree = (
                self.disability_degree_input.value()
                if category == "Menschen mit Beeinträchtigung"
                else None
            )

            has_housing_benefit = self._get_has_housing_benefit()

            evaluation = self.claim_service.evaluate_claim(
                incomes=incomes,
                expenses=expenses,
                adult_count=self.adult_count_input.value(),
                child_count=self.child_count_input.value(),
                category=category,
                disability_degree=disability_degree,
                has_housing_benefit=has_housing_benefit,
            )
        except Exception as exc:
            # Niemals den Dialog wegen eines Auswertungsfehlers schließen –
            # eingegebene Daten bleiben erhalten.
            QMessageBox.critical(
                self,
                "Fehler bei der Auswertung",
                f"Die Prüfung konnte nicht berechnet werden. Ihre Eingaben bleiben erhalten.\n\n{exc}",
            )
            self.status_label.setText("Auswertung fehlgeschlagen – Eingaben unverändert.")
            return

        self.current_evaluation = evaluation
        status_text = evaluation["status"]
        status_icon = "●"
        self.result_status.setText(f"{status_icon} {ClaimStatus.get_display(status_text)}")
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

    # ── Datenverlust-Schutz ───────────────────────────────────────────────
    def _has_user_input(self) -> bool:
        """True, wenn der Nutzer Werte eingegeben hat, die beim Schließen verloren gingen."""
        for widget in self.income_fields.values():
            text = widget.text().strip()
            if text and text not in ("0", "0.0", "0.00"):
                return True
        for amount, proof, note in self.expense_fields.values():
            text = amount.text().strip()
            if text and text not in ("0", "0.0", "0.00"):
                return True
            if proof.isChecked() or note.text().strip():
                return True
        return False

    def _confirm_discard(self) -> bool:
        """Fragt vor dem Schließen nach, wenn eine Prüfung läuft oder Daten erfasst wurden."""
        if self._saved:
            return True
        if not self._evaluation_started and not self._has_user_input():
            return True
        answer = QMessageBox.question(
            self,
            "Prüfung schließen?",
            "Es liegen nicht gespeicherte Prüfungsdaten vor.\n\n"
            "Wenn Sie jetzt schließen, gehen die eingegebenen Werte verloren.\n"
            "Möchten Sie die Prüfung wirklich schließen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def reject(self) -> None:
        # Fängt Escape-Taste und den "Schließen"-Button ab.
        if self._confirm_discard():
            if self._autosave_timer:
                self._autosave_timer.stop()
            super().reject()

    def closeEvent(self, event) -> None:
        # Fängt das Schließen über das Fenster-X ab.
        if self._confirm_discard():
            if self._autosave_timer:
                self._autosave_timer.stop()
            event.accept()
        else:
            event.ignore()

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
        has_housing_benefit = self._get_has_housing_benefit()

        if not category:
            QMessageBox.warning(self, "Ungültige Kategorie", "Bitte wählen Sie eine Kategorie für die Prüfung aus.")
            return

        try:
            # Sperre nochmals serverseitig prüfen (Defence-in-depth)
            from database.repositories.claim_repository import ClaimRepository
            eval_count = ClaimRepository().get_evaluation_count(self.claim_id)
            allowed, reason = self.re_evaluation_service.can_evaluate(self.claim_id, eval_count)
            if not allowed:
                QMessageBox.warning(
                    self, "Prüfung gesperrt",
                    f"{reason}\n\nNutzen Sie 'Freigabe anfordern', um eine Supervisor-Freigabe zu beantragen.",
                )
                self._update_lock_ui()
                return

            evaluation = self.claim_service.persist_evaluation(
                claim_id=self.claim_id,
                incomes=incomes,
                expenses=expenses,
                adult_count=self.adult_count_input.value(),
                child_count=self.child_count_input.value(),
                category=category,
                disability_degree=disability_degree,
                examiner_id=Session.get_user_id(),
                has_housing_benefit=has_housing_benefit,
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

        updated_claim = self.claim_service.get_claim_by_id(self.claim_id)
        # Prüfung wurde gespeichert → Entwurf löschen + Schließen ist gefahrlos.
        self._saved = True
        self._clear_draft()
        self.accept()

        # ── PostEvaluationPanel: Folgeaktionen direkt nach Prüfung ────────────
        try:
            from ui.pages.post_evaluation_panel import PostEvaluationPanel
            from services.document_package_service import DocumentPackageService
            from services.user_mail_service import UserMailService
            from services.wiedervorlage_service import WiedervorlageService
            panel = PostEvaluationPanel(
                claim=updated_claim or {},
                claim_service=self.claim_service,
                document_package_service=DocumentPackageService(),
                user_mail_service=UserMailService(),
                wiedervorlage_service=WiedervorlageService(),
                parent=self.parent(),
            )
            panel.exec()
        except Exception:
            pass

    def _update_lock_ui(self) -> None:
        """Aktualisiert den Lock-Banner und Buttons basierend auf dem aktuellen Sperr-Status."""
        if self.claim_id is None:
            return
        try:
            from database.repositories.claim_repository import ClaimRepository
            eval_count = ClaimRepository().get_evaluation_count(self.claim_id)
            state = self.re_evaluation_service.get_claim_lock_state(self.claim_id, eval_count)
            self._lock_state = state

            if state.get("locked"):
                self._lock_banner.setText(
                    f"Prüfung gesperrt: {state['reason']}"
                )
                self._lock_banner.setVisible(True)
                self.apply_status_button.setEnabled(False)
                # Zeige "Freigabe anfordern" nur wenn noch keine Anfrage gestellt
                has_pending = state.get("pending_request") is not None
                self._request_approval_button.setVisible(not has_pending)
                self._request_approval_button.setEnabled(not has_pending)
            elif eval_count > 0 and not state.get("privileged") and state.get("approved_request"):
                self._lock_banner.setText(
                    "Supervisor-Freigabe zur erneuten Prüfung liegt vor. Prüfung ist möglich."
                )
                self._lock_banner.setStyleSheet(
                    "color: #1a8f4a; background: #e8f8ed; border: 1px solid #b7e4cf; "
                    "border-radius: 6px; padding: 8px 12px; font-size: 12px;"
                )
                self._lock_banner.setVisible(True)
                self._request_approval_button.setVisible(False)
            else:
                self._lock_banner.setVisible(False)
                self._request_approval_button.setVisible(False)
        except Exception:
            pass

    def _on_request_re_evaluation(self) -> None:
        """Mitarbeiter fordert Freigabe zur erneuten Prüfung an."""
        from PyQt6.QtWidgets import QInputDialog
        reason, ok = QInputDialog.getText(
            self, "Freigabe anfordern",
            "Begründung (optional):",
        )
        if not ok:
            return
        try:
            self.re_evaluation_service.request_re_evaluation(
                self.claim_id, reason.strip() or None
            )
            QMessageBox.information(
                self,
                "Freigabe angefordert",
                "Die Freigabe zur erneuten Prüfung wurde beim Supervisor angefordert.\n"
                "Sie werden benachrichtigt, sobald eine Entscheidung vorliegt.",
            )
            self._update_lock_ui()
        except ValueError as exc:
            QMessageBox.warning(self, "Hinweis", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))

    def _load_checklist(self) -> None:
        """Lädt oder erzeugt automatisch die Unterlagen-Checkliste für diesen Fall."""
        if self.claim_id is None:
            return
        try:
            from ui.components.checklist_widget import ChecklistWidget

            # Vorhandene Items laden; wenn keine vorhanden → erste Vorlage auto-anwenden
            existing = self.checklist_service.list_claim_items(self.claim_id)
            if not existing:
                templates = self.checklist_service.list_templates()
                if templates:
                    self.checklist_service.apply_template(self.claim_id, templates[0]["id"])

            # Widget aufbauen
            if self._checklist_widget is not None:
                self._checklist_widget.deleteLater()
            self._checklist_placeholder.hide()

            self._checklist_widget = ChecklistWidget(
                claim_id=self.claim_id,
                checklist_service=self.checklist_service,
                parent=self,
            )
            self._checklist_widget.setMinimumHeight(160)
            self._checklist_inner_layout.addWidget(self._checklist_widget)
        except Exception:
            pass

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
            f"Standort: {claim.get('location_name','-')}, Kategorie: {claim.get('category_name','-')}, Status: {ClaimStatus.get_display(claim.get('status','-'))}"
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

        self._load_checklist()
        self._update_lock_ui()

        if claim.get("status") and claim.get("evaluation_reason") is not None:
            self.result_status.setText(f"● {ClaimStatus.get_display(claim['status'])}")
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

    # ── Autosave / Draft-Recovery ─────────────────────────────────────────

    def _init_autosave(self) -> None:
        """Startet den 30-Sekunden-Autosave-Timer und bietet ggf. einen gespeicherten Entwurf an."""
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(30_000)
        self._autosave_timer.timeout.connect(self._autosave_draft)
        self._autosave_timer.start()

        # Gespeicherten Entwurf anbieten (nur wenn Antrag bekannt)
        if self.claim_id:
            path = self._draft_path
            if path and path.exists():
                self._offer_draft_restore()

    @property
    def _draft_path(self) -> Path | None:
        """Pfad zur Entwurfsdatei für den aktuellen Antrag."""
        if not self.claim_id:
            return None
        from app.config import DATA_DIR
        drafts_dir = Path(DATA_DIR) / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        return drafts_dir / f"draft_evaluation_{self.claim_id}.json"

    def _autosave_draft(self) -> None:
        """Speichert den aktuellen Formularstand als Entwurf (aufgerufen alle 30 s)."""
        if self._saved or not self.claim_id:
            return
        if not self._evaluation_started and not self._has_user_input():
            return
        try:
            draft = {
                "claim_id": self.claim_id,
                "saved_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                "incomes": {k: self._parse_float(v) for k, v in self.income_fields.items()},
                "expenses": {
                    k: {
                        "amount": self._parse_float(amount),
                        "has_proof": proof.isChecked(),
                        "note": note.text().strip(),
                    }
                    for k, (amount, proof, note) in self.expense_fields.items()
                },
                "adult_count": self.adult_count_input.value(),
                "child_count": self.child_count_input.value(),
                "category": self.category_combo.currentText(),
                "disability_degree": self.disability_degree_input.value(),
                "has_housing_benefit": self._get_has_housing_benefit(),
                "housing_benefit_set": self.housing_benefit_set,
            }
            path = self._draft_path
            if path:
                path.write_text(
                    json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8"
                )
        except Exception:
            pass

    def _offer_draft_restore(self) -> None:
        """Fragt ob ein vorhandener Entwurf wiederhergestellt werden soll."""
        try:
            path = self._draft_path
            if not path or not path.exists():
                return
            data = json.loads(path.read_text(encoding="utf-8"))
            saved_at = data.get("saved_at", "unbekannt")
            answer = QMessageBox.question(
                self,
                "Entwurf wiederherstellen?",
                f"Es wurde ein gespeicherter Entwurf für diesen Antrag gefunden\n"
                f"(gespeichert: {saved_at}).\n\n"
                "Möchten Sie die Eingaben aus dem Entwurf wiederherstellen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._restore_from_draft(data)
        except Exception:
            pass

    def _restore_from_draft(self, data: dict) -> None:
        """Befüllt alle Formularfelder aus einem gespeicherten Entwurf."""
        try:
            for name, widget in self.income_fields.items():
                if name in data.get("incomes", {}):
                    widget.setText(f"{data['incomes'][name]:.2f}")

            for name, (amount, proof, note) in self.expense_fields.items():
                exp = data.get("expenses", {}).get(name)
                if exp:
                    amount.setText(f"{exp.get('amount', 0.0):.2f}")
                    proof.setChecked(bool(exp.get("has_proof", False)))
                    note.setText(exp.get("note", ""))

            if "adult_count" in data:
                self.adult_count_input.setValue(int(data["adult_count"]))
            if "child_count" in data:
                self.child_count_input.setValue(int(data["child_count"]))
            if "category" in data:
                idx = self.category_combo.findText(data["category"])
                if idx >= 0:
                    self.category_combo.setCurrentIndex(idx)
            if "disability_degree" in data:
                self.disability_degree_input.setValue(int(data["disability_degree"]))

            if data.get("housing_benefit_set"):
                self.housing_benefit_set = True
                self.housing_benefit_check.setChecked(
                    bool(data.get("has_housing_benefit"))
                )

            self._evaluation_started = True
            self.status_label.setText(
                f"Entwurf vom {data.get('saved_at', '?')} wiederhergestellt."
            )
        except Exception:
            pass

    def _clear_draft(self) -> None:
        """Löscht den Entwurf nach erfolgreichem Speichern."""
        try:
            path = self._draft_path
            if path and path.exists():
                path.unlink()
        except Exception:
            pass
