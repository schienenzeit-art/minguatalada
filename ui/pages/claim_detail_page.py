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
    QDateEdit,
    QTextEdit,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QDate

from services.card_service import CardService
from services.claim_service import ClaimService
from core.claim_status import ClaimStatus
from core.session import Session
from core.case_context import CaseContext
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
        header_layout.setColumnStretch(1, 1)
        header_layout.setColumnStretch(3, 1)

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
        person_layout.setColumnStretch(1, 1)
        person_layout.setColumnStretch(3, 1)

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
        self.income_group.setMinimumHeight(80)
        income_layout = QVBoxLayout()
        income_layout.setContentsMargins(12, 14, 12, 14)
        income_layout.setSpacing(4)
        self.income_container = QWidget()
        self.income_container.setStyleSheet("background: transparent;")
        self.income_inner = QVBoxLayout(self.income_container)
        self.income_inner.setContentsMargins(0, 0, 0, 0)
        self.income_inner.setSpacing(6)
        income_layout.addWidget(self.income_container)
        income_layout.addStretch()
        self.income_group.setLayout(income_layout)

        self.expense_group = QGroupBox("Ausgaben")
        self.expense_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.expense_group.setMinimumHeight(80)
        expense_layout = QVBoxLayout()
        expense_layout.setContentsMargins(12, 14, 12, 14)
        expense_layout.setSpacing(4)
        self.expense_container = QWidget()
        self.expense_container.setStyleSheet("background: transparent;")
        self.expense_inner = QVBoxLayout(self.expense_container)
        self.expense_inner.setContentsMargins(0, 0, 0, 0)
        self.expense_inner.setSpacing(6)
        expense_layout.addWidget(self.expense_container)
        expense_layout.addStretch()
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

        # Wiedervorlage
        review_group = QGroupBox("Wiedervorlage")
        review_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        review_layout = QHBoxLayout()
        review_layout.setContentsMargins(10, 12, 10, 12)
        review_layout.setSpacing(12)
        review_date_label = QLabel("Wiedervorlage am:")
        review_date_label.setStyleSheet("color: #4b5563; font-size: 13px;")
        self.review_date_edit = QDateEdit()
        self.review_date_edit.setCalendarPopup(True)
        self.review_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.review_date_edit.setDate(QDate.currentDate())
        self.review_date_edit.setSpecialValueText("Nicht gesetzt")
        self.review_date_edit.setMinimumDate(QDate(2000, 1, 1))
        save_review_btn = QPushButton("Speichern")
        save_review_btn.setFixedWidth(100)
        save_review_btn.clicked.connect(self._save_review_date)
        clear_review_btn = QPushButton("Löschen")
        clear_review_btn.setFixedWidth(80)
        clear_review_btn.clicked.connect(self._clear_review_date)
        self.review_date_label = QLabel("–")
        self.review_date_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #1a1917;")
        review_layout.addWidget(review_date_label)
        review_layout.addWidget(self.review_date_edit)
        review_layout.addWidget(save_review_btn)
        review_layout.addWidget(clear_review_btn)
        review_layout.addSpacing(24)
        review_layout.addWidget(QLabel("Aktuell:"))
        review_layout.addWidget(self.review_date_label)
        review_layout.addStretch()
        review_group.setLayout(review_layout)

        # Fallhistorie
        self.history_group = QGroupBox("Fallhistorie")
        self.history_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        history_layout = QVBoxLayout()
        history_layout.setContentsMargins(10, 12, 10, 12)
        history_layout.setSpacing(0)
        self.history_container = QWidget()
        self.history_container.setStyleSheet("background: transparent;")
        self.history_inner = QVBoxLayout(self.history_container)
        self.history_inner.setContentsMargins(0, 0, 0, 0)
        self.history_inner.setSpacing(4)
        history_layout.addWidget(self.history_container)
        history_layout.addStretch()
        self.history_group.setLayout(history_layout)

        self.cards_group = QGroupBox("Karten")
        self.cards_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        cards_layout = QVBoxLayout()
        cards_layout.setContentsMargins(10, 12, 10, 12)
        cards_layout.setSpacing(0)
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_inner = QVBoxLayout(self.cards_container)
        self.cards_inner.setContentsMargins(0, 0, 0, 0)
        self.cards_inner.setSpacing(4)
        cards_layout.addWidget(self.cards_container)
        cards_layout.addStretch()
        self.cards_group.setLayout(cards_layout)

        # Interne Notizen
        self.notes_group = QGroupBox("Interne Notizen")
        self.notes_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        notes_layout = QVBoxLayout()
        notes_layout.setContentsMargins(10, 12, 10, 12)
        notes_layout.setSpacing(6)
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Neue Notiz eingeben…")
        self.notes_input.setFixedHeight(70)
        notes_add_btn = QPushButton("Notiz hinzufügen")
        notes_add_btn.setFixedWidth(150)
        notes_add_btn.clicked.connect(self._add_note)
        notes_top = QHBoxLayout()
        notes_top.addWidget(self.notes_input)
        notes_top.addWidget(notes_add_btn, alignment=Qt.AlignmentFlag.AlignTop)
        notes_layout.addLayout(notes_top)
        self.notes_container = QWidget()
        self.notes_container.setStyleSheet("background: transparent;")
        self.notes_inner = QVBoxLayout(self.notes_container)
        self.notes_inner.setContentsMargins(0, 0, 0, 0)
        self.notes_inner.setSpacing(4)
        notes_layout.addWidget(self.notes_container)
        self.notes_group.setLayout(notes_layout)

        # Aktivitäts-Feed
        self.activity_group = QGroupBox("Aktivitäten")
        self.activity_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        activity_layout = QVBoxLayout()
        activity_layout.setContentsMargins(10, 12, 10, 12)
        activity_layout.setSpacing(0)
        self.activity_container = QWidget()
        self.activity_container.setStyleSheet("background: transparent;")
        self.activity_inner = QVBoxLayout(self.activity_container)
        self.activity_inner.setContentsMargins(0, 0, 0, 0)
        self.activity_inner.setSpacing(4)
        activity_layout.addWidget(self.activity_container)
        activity_layout.addStretch()
        self.activity_group.setLayout(activity_layout)

        action_layout = QHBoxLayout()
        action_layout.addStretch()
        self.clone_button = QPushButton("Fall klonen")
        self.clone_button.setToolTip("Erstellt einen neuen Antrag mit denselben Stammdaten")
        self.clone_button.clicked.connect(self.on_clone_claim)
        self.widerspruch_button = QPushButton("Widerspruch einlegen")
        self.widerspruch_button.setToolTip("Widerspruchsverfahren starten und Frist setzen")
        self.widerspruch_button.clicked.connect(self.on_widerspruch)
        self.create_card_button = QPushButton("Neue Karte erstellen")
        self.create_card_button.clicked.connect(self.on_create_card)
        self.evaluation_button = QPushButton("Prüfung durchführen")
        self.evaluation_button.setObjectName("primaryButton")
        self.evaluation_button.clicked.connect(self.open_evaluation_dialog)
        action_layout.addWidget(self.clone_button)
        action_layout.addWidget(self.widerspruch_button)
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
        content_layout.addWidget(review_group)
        content_layout.addWidget(self.history_group)
        content_layout.addWidget(self.notes_group)
        content_layout.addWidget(self.activity_group)
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
        # CaseContext für Topbar-Aktionen aktualisieren
        CaseContext.set(self.claim_id, claim)

        self.claim = claim
        self.case_number_label.setText(claim.get("case_number") or "-")
        self.person_label.setText(claim.get("person_display_name") or "-")
        self.category_label.setText(claim.get("category_name") or "-")
        self.user_label.setText(claim["user_name"] or "-")
        self.status_label.setText(ClaimStatus.get_display(claim["status"] or "") or "-")
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

        raw_status = claim["status"] or ""
        self.eval_status_label.setText(ClaimStatus.get_display(raw_status) or "-")
        self._apply_status_style(raw_status)
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
        self._clear_layout(self.income_inner)
        if incomes:
            for item in incomes:
                self.income_inner.addWidget(
                    self._make_finance_row(item["type"], f"{item['amount']:.2f} €")
                )
        else:
            lbl = QLabel("-")
            lbl.setStyleSheet("color: #9ca3af; font-size: 13px;")
            self.income_inner.addWidget(lbl)

        expenses = claim.get("expenses") or []
        self._clear_layout(self.expense_inner)
        if expenses:
            for item in expenses:
                proof_badge = "Nachweis ✓" if item.get("has_proof") else "kein Nachweis"
                note = item.get("note") or ""
                sub = proof_badge + (f" · {note}" if note else "")
                self.expense_inner.addWidget(
                    self._make_finance_row(item["type"], f"{item['amount']:.2f} €", sub)
                )
        else:
            lbl = QLabel("-")
            lbl.setStyleSheet("color: #9ca3af; font-size: 13px;")
            self.expense_inner.addWidget(lbl)

        self.evaluation_button.setEnabled(True)
        wfrist = claim.get("widerspruch_frist")
        self.widerspruch_button.setEnabled(claim.get("status") == "ABGELEHNT" or bool(wfrist))

        review_date = claim.get("review_date")
        if review_date:
            self.review_date_label.setText(review_date)
            try:
                parts = review_date.split("-")
                self.review_date_edit.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
            except Exception:
                pass
        else:
            self.review_date_label.setText("–")

        self.load_history()
        self.load_notes()
        self.load_activity_feed()
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
        
        self._clear_layout(self.cards_inner)
        if cards:
            for card in cards:
                card_number = card.get("card_number", "?")
                status = card.get("status", "?")
                expiry = card.get("expiry_date", "-")
                status_display = self.card_service.get_card_status_display(status)
                self.cards_inner.addWidget(
                    self._make_finance_row(card_number, status_display, f"Ablauf: {expiry}")
                )
        else:
            lbl = QLabel("Keine Karten für diesen Fall.")
            lbl.setStyleSheet("color: #9ca3af; font-size: 13px;")
            self.cards_inner.addWidget(lbl)
        
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

    def load_history(self) -> None:
        self._clear_layout(self.history_inner)
        history = self.claim_service.get_claim_history(self.claim_id)
        if not history:
            lbl = QLabel("Noch keine Statusänderungen aufgezeichnet.")
            lbl.setStyleSheet("color: #9ca3af; font-size: 13px;")
            self.history_inner.addWidget(lbl)
            return
        for entry in history:
            old = ClaimStatus.get_display(entry.get("old_status") or "") or "–"
            new = ClaimStatus.get_display(entry.get("new_status") or "") or "?"
            by = entry.get("changed_by_name") or "System"
            at = (entry.get("changed_at") or "")[:16].replace("T", " ")
            note = entry.get("note") or ""
            sub = f"{by} · {at}" + (f" · {note}" if note else "")
            arrow = f"{old} → {new}"
            self.history_inner.addWidget(self._make_finance_row(arrow, "", sub))

    def load_notes(self) -> None:
        self._clear_layout(self.notes_inner)
        notes = self.claim_service.get_claim_notes(self.claim_id)
        if not notes:
            lbl = QLabel("Noch keine Notizen.")
            lbl.setStyleSheet("color: #9ca3af; font-size: 13px;")
            self.notes_inner.addWidget(lbl)
            return
        for note in notes:
            author = note.get("author_name") or "–"
            at = (note.get("created_at") or "")[:16].replace("T", " ")
            text = note.get("note_text", "")
            self.notes_inner.addWidget(
                self._make_finance_row(text, "", f"{author} · {at}")
            )

    def _add_note(self) -> None:
        text = self.notes_input.toPlainText().strip()
        if not text:
            return
        self.claim_service.add_claim_note(self.claim_id, text)
        self.notes_input.clear()
        self.load_notes()
        self.load_activity_feed()

    def load_activity_feed(self) -> None:
        self._clear_layout(self.activity_inner)
        events = self.claim_service.get_activity_feed(self.claim_id)
        if not events:
            lbl = QLabel("Noch keine Aktivitäten.")
            lbl.setStyleSheet("color: #9ca3af; font-size: 13px;")
            self.activity_inner.addWidget(lbl)
            return
        icon_map = {"status": "◎", "note": "✏"}
        for ev in events:
            icon = icon_map.get(ev["type"], "·")
            ts = (ev.get("timestamp") or "")[:16].replace("T", " ")
            label = f"{icon} {ev.get('text', '')}"
            sub = f"{ev.get('author', '–')} · {ts}"
            if ev.get("detail"):
                sub += f" · {ev['detail']}"
            self.activity_inner.addWidget(self._make_finance_row(label, "", sub))

    def on_widerspruch(self) -> None:
        if not self.claim:
            return
        frist, ok = __import__("PyQt6.QtWidgets", fromlist=["QInputDialog"]).QInputDialog.getText(
            self, "Widerspruch einlegen",
            "Frist (YYYY-MM-DD):",
            text=QDate.currentDate().addDays(30).toString("yyyy-MM-dd"),
        )
        if not ok:
            return
        if self.claim_service.set_widerspruch(self.claim_id, frist.strip() or None):
            QMessageBox.information(self, "Widerspruch", f"Widerspruch eingelegt, Frist: {frist}.")
            self.load_claim()
        else:
            QMessageBox.warning(self, "Fehler", "Widerspruch konnte nicht gesetzt werden.")

    def _save_review_date(self) -> None:
        if not self.claim:
            return
        date_val = self.review_date_edit.date().toString("yyyy-MM-dd")
        if self.claim_service.set_review_date(self.claim_id, date_val):
            self.review_date_label.setText(date_val)
            QMessageBox.information(self, "Wiedervorlage", f"Wiedervorlage gesetzt auf {date_val}.")
        else:
            QMessageBox.warning(self, "Fehler", "Wiedervorlage konnte nicht gespeichert werden.")

    def _clear_review_date(self) -> None:
        if not self.claim:
            return
        if self.claim_service.set_review_date(self.claim_id, None):
            self.review_date_label.setText("–")
            self.review_date_edit.setDate(QDate.currentDate())

    def on_clone_claim(self) -> None:
        if not self.claim:
            return
        reply = QMessageBox.question(
            self,
            "Fall klonen",
            f"Möchten Sie einen neuen Antrag auf Basis von {self.claim.get('case_number', '')} erstellen?\n"
            "Alle Stamm- und Haushaltsdaten werden übernommen.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        result = self.claim_service.clone_claim(self.claim_id)
        if result:
            reply = QMessageBox.question(
                self,
                "Fall geklont",
                f"Neuer Fall {result['case_number']} wurde erstellt.\nMöchten Sie den neuen Fall jetzt öffnen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                new_dialog = ClaimDetailPage(
                    claim_id=result["id"],
                    claim_service=self.claim_service,
                    card_service=self.card_service,
                )
                new_dialog.exec()
        else:
            QMessageBox.warning(self, "Fehler", "Fall konnte nicht geklont werden.")

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _make_finance_row(self, label: str, value: str, sub: str = "") -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(row)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.setSpacing(1)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #4b5563; font-size: 13px;")
        val = QLabel(value)
        val.setStyleSheet("font-size: 13px; font-weight: 600; color: #1a1917;")
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(lbl)
        top_row.addStretch()
        top_row.addWidget(val)
        outer.addLayout(top_row)

        if sub:
            sub_lbl = QLabel(sub)
            sub_lbl.setStyleSheet("color: #9ca3af; font-size: 11px;")
            sub_lbl.setWordWrap(True)
            outer.addWidget(sub_lbl)

        return row

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
        # CaseContext aktualisieren damit Topbar-Aktionen fallbezogen sind
        CaseContext.set(self.claim_id, self.claim)
        dialog = ClaimEvaluationDialog(self.claim_id, self.claim_service)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_claim()
            # CaseContext nach Reload aktualisieren
            CaseContext.set(self.claim_id, self.claim)
