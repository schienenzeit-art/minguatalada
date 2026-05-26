from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGridLayout,
    QLabel,
    QGroupBox,
    QDialogButtonBox,
    QPushButton,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
)
from PyQt6.QtCore import Qt

from services.card_service import CardService
from services.claim_service import ClaimService
from core.session import Session
from ui.pages.claim_evaluation_dialog import ClaimEvaluationDialog
from ui.pages.person_dossier_dialog import PersonDossierDialog


class ClaimDetailPage(QDialog):
    def __init__(
        self,
        claim_id: int,
        claim_service: ClaimService | None = None,
        card_service: CardService | None = None,
    ):
        super().__init__()
        # allow minimize / maximize on opened dialogs
        flags = self.windowFlags()
        flags |= Qt.WindowType.Window
        flags |= Qt.WindowType.WindowMinimizeButtonHint
        flags |= Qt.WindowType.WindowMaximizeButtonHint
        self.setWindowFlags(flags)
        self.claim_id = claim_id
        self.claim_service = claim_service or ClaimService()
        self.card_service = card_service or CardService()
        self.claim = None
        self.setup_ui()
        self.load_claim()

    def setup_ui(self):
        self.setWindowTitle("Anspruchsdetails")
        self.setMinimumSize(900, 700)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(18)

        title_label = QLabel("Anspruchsdetails")
        title_label.setStyleSheet(
            "font-size: 22px; font-weight: 700; margin-bottom: 4px;"
        )
        subtitle_label = QLabel("Übersicht zum Antrag, Haushalt, Finanzen und Prüfergebnis")
        subtitle_label.setStyleSheet("color: #556982; margin-bottom: 16px;")

        header_box = QGroupBox("Fallübersicht")
        header_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        header_layout = QGridLayout()
        header_layout.setHorizontalSpacing(24)
        header_layout.setVerticalSpacing(12)

        self.case_number_label = QLabel("-")
        self.person_label = QPushButton("-")
        self.person_label.setFlat(True)
        self.person_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.person_label.clicked.connect(self.open_person_dossier)
        self.location_label = QLabel("-")
        self.user_label = QLabel("-")
        self.status_label = QLabel("-")
        self.category_label = QLabel("-")
        self.period_label = QLabel("-")
        self.description_label = QLabel("-")
        self.examiner_label = QLabel("-")
        self.evaluation_date_label = QLabel("-")
        self.created_label = QLabel("-")
        self.updated_label = QLabel("-")

        self.description_label.setWordWrap(True)

        header_layout.addWidget(QLabel("Fallnummer:"), 0, 0)
        header_layout.addWidget(self.case_number_label, 0, 1)
        header_layout.addWidget(QLabel("Person:"), 0, 2)
        header_layout.addWidget(self.person_label, 0, 3)

        header_layout.addWidget(QLabel("Standort:"), 1, 0)
        header_layout.addWidget(self.location_label, 1, 1)
        header_layout.addWidget(QLabel("Status:"), 1, 2)
        header_layout.addWidget(self.status_label, 1, 3)

        header_layout.addWidget(QLabel("Kategorie:"), 2, 0)
        header_layout.addWidget(self.category_label, 2, 1)
        header_layout.addWidget(QLabel("Prüfer:"), 2, 2)
        header_layout.addWidget(self.examiner_label, 2, 3)

        header_layout.addWidget(QLabel("Prüfdatum:"), 3, 0)
        header_layout.addWidget(self.evaluation_date_label, 3, 1)
        header_layout.addWidget(QLabel("Zeitraum:"), 3, 2)
        header_layout.addWidget(self.period_label, 3, 3)

        header_layout.addWidget(QLabel("Beschreibung:"), 4, 0)
        header_layout.addWidget(self.description_label, 4, 1, 1, 3)

        header_box.setLayout(header_layout)

        self.person_group = QGroupBox("Stammdaten")
        person_layout = QGridLayout()
        person_layout.setHorizontalSpacing(24)
        person_layout.setVerticalSpacing(12)

        self.address_label = QLabel("-")
        self.city_label = QLabel("-")
        self.email_label = QLabel("-")
        self.household_size_label = QLabel("-")
        self.adult_count_label = QLabel("-")
        self.child_count_label = QLabel("-")
        self.disability_label = QLabel("-")

        for label in [
            self.address_label,
            self.city_label,
            self.email_label,
            self.household_size_label,
            self.adult_count_label,
            self.child_count_label,
            self.disability_label,
        ]:
            label.setWordWrap(True)

        person_layout.addWidget(QLabel("Adresse:"), 0, 0)
        person_layout.addWidget(self.address_label, 0, 1)
        person_layout.addWidget(QLabel("Ort:"), 0, 2)
        person_layout.addWidget(self.city_label, 0, 3)

        person_layout.addWidget(QLabel("E-Mail:"), 1, 0)
        person_layout.addWidget(self.email_label, 1, 1)
        person_layout.addWidget(QLabel("Haushaltsgröße:"), 1, 2)
        person_layout.addWidget(self.household_size_label, 1, 3)

        person_layout.addWidget(QLabel("Erwachsene:"), 2, 0)
        person_layout.addWidget(self.adult_count_label, 2, 1)
        person_layout.addWidget(QLabel("Kinder:"), 2, 2)
        person_layout.addWidget(self.child_count_label, 2, 3)

        person_layout.addWidget(QLabel("Behinderungsgrad:"), 3, 0)
        person_layout.addWidget(self.disability_label, 3, 1)

        self.person_group.setLayout(person_layout)

        finance_row = QHBoxLayout()
        finance_row.setSpacing(18)

        self.income_group = QGroupBox("Einnahmen")
        self.income_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.income_list = QLabel("-")
        self.income_list.setWordWrap(True)
        income_layout = QVBoxLayout()
        income_layout.addWidget(self.income_list)
        self.income_group.setLayout(income_layout)

        self.expense_group = QGroupBox("Ausgaben")
        self.expense_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.expense_list = QLabel("-")
        self.expense_list.setWordWrap(True)
        expense_layout = QVBoxLayout()
        expense_layout.addWidget(self.expense_list)
        self.expense_group.setLayout(expense_layout)

        finance_row.addWidget(self.income_group)
        finance_row.addWidget(self.expense_group)

        self.evaluation_group = QGroupBox("Prüfergebnis")
        evaluation_layout = QVBoxLayout()
        evaluation_layout.setSpacing(14)

        self.eval_status_label = QLabel("-")
        self.eval_status_label.setStyleSheet(
            "font-size: 18px; font-weight: 700; padding: 12px; border-radius: 10px;"
        )
        self.eval_reason_label = QLabel("-")
        self.eval_reason_label.setWordWrap(True)
        self.free_income_label = QLabel("-")
        self.entitlement_label = QLabel("-")
        self.hardship_label = QLabel("-")
        self.calc_details_label = QLabel("-")
        self.calc_details_label.setWordWrap(True)

        summary_layout = QFormLayout()
        summary_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        summary_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        summary_layout.setHorizontalSpacing(24)
        summary_layout.setVerticalSpacing(8)
        summary_layout.addRow("Status:", self.eval_status_label)
        summary_layout.addRow("Begründung:", self.eval_reason_label)
        summary_layout.addRow("Frei verfügbar:", self.free_income_label)
        summary_layout.addRow("Anspruchsgrenze:", self.entitlement_label)
        summary_layout.addRow("Härtefallgrenze:", self.hardship_label)
        summary_layout.addRow("Berechnungsdetails:", self.calc_details_label)

        evaluation_layout.addLayout(summary_layout)
        self.evaluation_group.setLayout(evaluation_layout)

        self.cards_group = QGroupBox("Karten")
        cards_layout = QVBoxLayout()
        self.cards_list_label = QLabel("-")
        self.cards_list_label.setWordWrap(True)
        cards_layout.addWidget(self.cards_list_label)
        self.cards_group.setLayout(cards_layout)

        action_layout = QHBoxLayout()
        action_layout.addStretch()
        self.create_card_button = QPushButton("Neue Karte erstellen")
        self.create_card_button.clicked.connect(self.on_create_card)
        self.evaluation_button = QPushButton("Prüfung durchführen")
        self.evaluation_button.setObjectName("primaryButton")
        self.evaluation_button.clicked.connect(self.open_evaluation_dialog)
        action_layout.addWidget(self.create_card_button)
        action_layout.addWidget(self.evaluation_button)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        content_layout.addWidget(title_label)
        content_layout.addWidget(subtitle_label)
        content_layout.addWidget(header_box)
        content_layout.addWidget(self.person_group)
        content_layout.addLayout(finance_row)
        content_layout.addWidget(self.evaluation_group)
        content_layout.addWidget(self.cards_group)
        content_layout.addLayout(action_layout)
        content_layout.addWidget(buttons)

        scroll.setWidget(content_widget)
        outer_layout.addWidget(scroll)

    def load_claim(self):
        claim = self.claim_service.get_claim_by_id(self.claim_id)
        if claim is None:
            self.description_label.setText("Anspruch nicht gefunden.")
            self.evaluation_button.setEnabled(False)
            return

        self.claim = claim
        self.case_number_label.setText(claim.get("case_number") or "-")
        self.person_label.setText(claim.get("person_display_name") or "-")
        self.category_label.setText(claim.get("category_name") or "-")
        self.user_label.setText(claim["user_name"] or "-")
        self.status_label.setText(claim["status"] or "-")
        self.location_label.setText(claim["location_name"] or "-")
        self.period_label.setText(
            f"{claim['start_date'] or '-'} bis {claim['end_date'] or '-'}"
        )
        self.description_label.setText(claim["description"] or "-")
        self.person_label.setEnabled(bool(claim.get("person_id")))
        if claim.get("person_display_name"):
            self.person_label.setText(claim.get("person_display_name"))
            self.person_label.setStyleSheet(
                "text-align:left; color:#1a73e8; text-decoration: underline; background: transparent; border: none;"
            )
        else:
            self.person_label.setText("-")
            self.person_label.setStyleSheet("")
        self.created_label.setText(claim["created_at"] or "-")
        self.updated_label.setText(claim["updated_at"] or "-")
        self.examiner_label.setText(claim.get("examiner_name") or "-")
        self.evaluation_date_label.setText(claim.get("evaluation_date") or "-")

        self.address_label.setText(claim.get("person_address") or "-")
        city_text = ""
        if claim.get("person_postal_code") and claim.get("person_city"):
            city_text = f"{claim['person_postal_code']} {claim['person_city']}"
        elif claim.get("person_city"):
            city_text = claim["person_city"]
        self.city_label.setText(city_text or "-")
        self.email_label.setText(claim.get("person_email") or "-")

        adult_count = claim.get("adult_count") or 0
        child_count = claim.get("child_count") or 0
        household_size = adult_count + child_count
        self.household_size_label.setText(str(household_size) if household_size else "-")
        self.adult_count_label.setText(str(adult_count) if adult_count else "-" )
        self.child_count_label.setText(str(child_count) if child_count else "-")
        disability_text = (
            f"{claim.get('disability_degree')} %"
            if claim.get("disability_degree") is not None
            else "-"
        )
        self.disability_label.setText(disability_text)

        status_text = claim["status"] or "-"
        self.eval_status_label.setText(status_text)
        self._apply_status_style(status_text)
        self.eval_reason_label.setText(claim.get("evaluation_reason") or "-")
        self.free_income_label.setText(
            f"{claim.get('free_income', '-'):.2f} €" if claim.get("free_income") is not None else "-"
        )
        self.entitlement_label.setText(
            f"{claim.get('entitlement_limit', '-'):.2f} €" if claim.get("entitlement_limit") is not None else "-"
        )
        self.hardship_label.setText(
            f"{claim.get('hardship_limit', '-'):.2f} €" if claim.get("hardship_limit") is not None else "-"
        )
        details = claim.get("evaluation_details")
        if isinstance(details, dict):
            detail_lines = []
            if details.get("additional_adults") is not None:
                detail_lines.append(f"Weitere Erwachsene: {details['additional_adults']}")
            if details.get("child_count") is not None:
                detail_lines.append(f"Kinder: {details['child_count']}")
            if details.get("incomes") is not None:
                detail_lines.append(f"Einkommenspositionen: {len(details['incomes'])}")
            if details.get("expenses") is not None:
                detail_lines.append(f"Ausgabenpositionen: {len(details['expenses'])}")
            self.calc_details_label.setText("; ".join(detail_lines) if detail_lines else "-")
        else:
            self.calc_details_label.setText(str(details) if details is not None else "-")

        incomes = claim.get("incomes") or []
        if incomes:
            self.income_list.setText("\n".join([f"{item['type']}: {item['amount']:.2f} €" for item in incomes]))
        else:
            self.income_list.setText("-")

        expenses = claim.get("expenses") or []
        if expenses:
            expense_lines = []
            for item in expenses:
                proof = "Ja" if item.get("has_proof") else "Nein"
                note = item.get("note") or ""
                expense_lines.append(
                    f"{item['type']}: {item['amount']:.2f} € / Nachweis: {proof}" + (f" / {note}" if note else "")
                )
            self.expense_list.setText("\n".join(expense_lines))
        else:
            self.expense_list.setText("-")

        self.evaluation_button.setEnabled(True)

        # Karten laden und anzeigen
        self.load_cards()

    def open_person_dossier(self):
        if not self.claim or not self.claim.get("person_id"):
            QMessageBox.information(self, "Person nicht verfügbar", "Keine Person zum Anzeigen gefunden.")
            return

        dialog = PersonDossierDialog(person_id=self.claim["person_id"])
        dialog.exec()

    def load_cards(self):
        """Lädt und zeigt Karten für den Fall an."""
        cards = self.card_service.get_cards_for_claim(self.claim_id)
        
        if cards:
            card_lines = []
            for card in cards:
                card_number = card.get("card_number", "?")
                status = card.get("status", "?")
                expiry = card.get("expiry_date", "-")
                status_display = self.card_service.get_card_status_display(status)
                card_lines.append(f"{card_number} – {status_display} – Ablauf: {expiry}")
            
            self.cards_list_label.setText("\n".join(card_lines))
        else:
            self.cards_list_label.setText("Keine Karten für diesen Fall.")
        
        # Button Aktivierung basierend auf Fallstatus
        can_create, reason = self.card_service.can_create_card_for_claim(self.claim_id)
        self.create_card_button.setEnabled(can_create)
        if not can_create:
            self.create_card_button.setToolTip(reason)

    def on_create_card(self):
        """Handler für "Neue Karte erstellen" Button."""
        can_create, reason = self.card_service.can_create_card_for_claim(self.claim_id)
        
        if not can_create:
            QMessageBox.warning(
                self,
                "Kartenerstellung nicht möglich",
                reason,
            )
            return
        
        current_user_id = Session.get_user_id()
        if current_user_id is None:
            QMessageBox.critical(
                self,
                "Fehler",
                "Authentifizierter Benutzer nicht gefunden.",
            )
            return

        card = self.card_service.create_card(
            claim_id=self.claim_id,
            created_by=current_user_id,
        )
        
        if card:
            QMessageBox.information(
                self,
                "Kartenerstellung erfolgreich",
                f"Karte {card['card_number']} wurde erfolgreich erstellt.",
            )
            self.load_cards()
        else:
            QMessageBox.critical(
                self,
                "Fehler",
                "Kartenerstellung ist fehlgeschlagen.",
            )

    def _apply_status_style(self, status: str) -> None:
        if status == "ANSPRUCHSBERECHTIGT":
            self.eval_status_label.setStyleSheet(
                "font-size: 18px; font-weight: 700; padding: 12px; border-radius: 10px; background-color: #e7f7ef; color: #1f7a5a; border: 1px solid #b7e4cf;"
            )
        elif status == "HAERTEFALL":
            self.eval_status_label.setStyleSheet(
                "font-size: 18px; font-weight: 700; padding: 12px; border-radius: 10px; background-color: #fff7e6; color: #9a6700; border: 1px solid #f7d9a3;"
            )
        elif status == "ABGELEHNT":
            self.eval_status_label.setStyleSheet(
                "font-size: 18px; font-weight: 700; padding: 12px; border-radius: 10px; background-color: #fdecec; color: #b42318; border: 1px solid #f5c2c0;"
            )
        else:
            self.eval_status_label.setStyleSheet(
                "font-size: 18px; font-weight: 700; padding: 12px; border-radius: 10px; background-color: #eef3f7; color: #334e68; border: 1px solid #d8e2ec;"
            )

    def open_evaluation_dialog(self):
        dialog = ClaimEvaluationDialog(self.claim_id, self.claim_service)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_claim()
