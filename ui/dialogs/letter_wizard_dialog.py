"""Schnellzugang für Brief-/Bescheid-Erstellung aus der Topbar."""
from datetime import date

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFormLayout, QTextEdit,
    QDialogButtonBox, QMessageBox, QGroupBox,
)
from PyQt6.QtCore import Qt


class LetterWizardDialog(QDialog):
    """Wizard: Fall suchen → Vorlage wählen → PDF erstellen / E-Mail senden."""

    def __init__(
        self,
        template_type: str | None = None,
        claim_service=None,
        template_service=None,
        pdf_service=None,
        parent=None,
    ):
        super().__init__(parent)
        self._template_type    = template_type
        self._claim_service    = claim_service
        self._template_service = template_service
        self._pdf_service      = pdf_service
        self._claim: dict | None = None
        self._templates: list[dict] = []
        self._pdf_path: str | None = None

        title = {"BESCHEID": "Bescheid erstellen", "BRIEF": "Brief erstellen"}.get(
            template_type or "", "Dokument erstellen"
        )
        self.setWindowTitle(title)
        self.setMinimumWidth(680)
        self.setMinimumHeight(560)
        self._setup_ui()
        self._load_templates()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # ── 1. Fall suchen ────────────────────────────────────────────────────
        search_box = QGroupBox("1. Fall suchen")
        search_form = QFormLayout(search_box)
        search_form.setSpacing(8)
        self._case_input = QLineEdit()
        self._case_input.setPlaceholderText("Aktenzeichen eingeben …")
        search_btn = QPushButton("Suchen")
        search_btn.setObjectName("SoftButton")
        search_btn.clicked.connect(self._search_claim)
        row = QHBoxLayout()
        row.addWidget(self._case_input, 1)
        row.addWidget(search_btn)
        search_form.addRow("Aktenzeichen:", row)
        self._claim_info = QLabel("Kein Fall geladen.")
        self._claim_info.setStyleSheet("color: #666; font-size: 11px;")
        self._claim_info.setWordWrap(True)
        search_form.addRow("", self._claim_info)
        layout.addWidget(search_box)

        # ── 2. Vorlage wählen ─────────────────────────────────────────────────
        tpl_box = QGroupBox("2. Vorlage wählen")
        tpl_form = QFormLayout(tpl_box)
        tpl_form.setSpacing(8)
        self._tpl_combo = QComboBox()
        self._tpl_combo.currentIndexChanged.connect(self._update_preview)
        tpl_form.addRow("Vorlage:", self._tpl_combo)
        layout.addWidget(tpl_box)

        # ── 3. Vorschau ───────────────────────────────────────────────────────
        prev_box = QGroupBox("3. Vorschau")
        prev_layout = QVBoxLayout(prev_box)
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setMinimumHeight(160)
        self._preview.setStyleSheet("font-size: 11px; background: #fafafa;")
        prev_layout.addWidget(self._preview)
        layout.addWidget(prev_box)

        # ── Aktions-Buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        pdf_btn = QPushButton("PDF erstellen & öffnen")
        pdf_btn.setObjectName("PrimaryButton")
        pdf_btn.clicked.connect(self._generate_pdf)
        btn_row.addWidget(pdf_btn)

        save_btn = QPushButton("PDF speichern unter …")
        save_btn.setObjectName("SoftButton")
        save_btn.clicked.connect(self._save_pdf)
        btn_row.addWidget(save_btn)

        mail_btn = QPushButton("Per E-Mail senden")
        mail_btn.setObjectName("SecondaryButton")
        mail_btn.clicked.connect(self._send_email)
        btn_row.addWidget(mail_btn)

        btn_row.addStretch()
        close_btn = QPushButton("Schließen")
        close_btn.setObjectName("SoftButton")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    # ── Datenladen ────────────────────────────────────────────────────────────
    def _load_templates(self):
        if self._template_service is None:
            return
        try:
            all_tpl = self._template_service.list_templates(include_inactive=False)
            self._templates = [
                t for t in all_tpl
                if self._template_type is None or t.get("template_type") == self._template_type
            ]
            self._tpl_combo.clear()
            for t in self._templates:
                label = f"{t['name']} [{t.get('template_type','')}]"
                self._tpl_combo.addItem(label, t["id"])
        except Exception:
            pass

    def _search_claim(self):
        case_number = self._case_input.text().strip()
        if not case_number or self._claim_service is None:
            return
        try:
            claims = self._claim_service.list_claims()
            found = next(
                (c for c in claims if c.get("case_number", "").lower() == case_number.lower()),
                None,
            )
            if found:
                self._claim = self._claim_service.get_claim_by_id(found["id"])
                from core.claim_status import ClaimStatus
                status = ClaimStatus.get_display(self._claim.get("status", ""))
                self._claim_info.setText(
                    f"Fall: {self._claim.get('case_number')} | "
                    f"Person: {self._claim.get('person_first_name','')} "
                    f"{self._claim.get('person_last_name','')} | Status: {status}"
                )
                self._claim_info.setStyleSheet("color: #1a8f4a; font-size: 11px;")
                self._update_preview()
            else:
                self._claim_info.setText(f"Kein Fall mit Aktenzeichen '{case_number}' gefunden.")
                self._claim_info.setStyleSheet("color: #c0362a; font-size: 11px;")
        except Exception as exc:
            self._claim_info.setText(f"Fehler: {exc}")

    def _get_context(self) -> dict:
        if self._claim and self._template_service:
            from services.document_template_service import build_claim_context
            return build_claim_context(self._claim)
        return {"DATUM": date.today().strftime("%d.%m.%Y")}

    def _update_preview(self):
        if self._template_service is None or not self._templates:
            return
        tpl_id = self._tpl_combo.currentData()
        if tpl_id is None:
            return
        try:
            rendered = self._template_service.render(tpl_id, self._get_context())
            self._preview.setPlainText(rendered)
        except Exception:
            pass

    # ── Aktionen ──────────────────────────────────────────────────────────────
    def _generate_pdf(self):
        tpl_id = self._tpl_combo.currentData()
        if tpl_id is None:
            QMessageBox.warning(self, "Hinweis", "Bitte eine Vorlage auswählen.")
            return
        if self._pdf_service is None:
            QMessageBox.warning(self, "Hinweis", "PDF-Service nicht verfügbar.")
            return
        try:
            path = self._pdf_service.generate_letter_pdf(tpl_id, self._get_context())
            self._pdf_path = path
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))

    def _save_pdf(self):
        from PyQt6.QtWidgets import QFileDialog
        tpl_id = self._tpl_combo.currentData()
        if tpl_id is None:
            QMessageBox.warning(self, "Hinweis", "Bitte eine Vorlage auswählen.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "PDF speichern", "Brief.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            self._pdf_service.generate_letter_pdf(tpl_id, self._get_context(), file_path=path)
            self._pdf_path = path
            QMessageBox.information(self, "Gespeichert", f"PDF gespeichert unter:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))

    def _send_email(self):
        from PyQt6.QtWidgets import QInputDialog
        ctx   = self._get_context()
        email = (self._claim or {}).get("person_email", "") or ""
        to, ok = QInputDialog.getText(
            self, "E-Mail senden", "Empfänger-E-Mail:", text=email
        )
        if not ok or not to.strip():
            return

        tpl_id = self._tpl_combo.currentData()
        if tpl_id is None:
            QMessageBox.warning(self, "Hinweis", "Bitte eine Vorlage auswählen.")
            return
        try:
            if not self._pdf_path:
                self._pdf_path = self._pdf_service.generate_letter_pdf(tpl_id, ctx)
            from services.mail_service import MailService
            svc  = MailService()
            name = f"{ctx.get('VORNAME','')} {ctx.get('NACHNAME','')}".strip()
            svc.send_letter(to_email=to.strip(), person_name=name, pdf_path=self._pdf_path)
            QMessageBox.information(self, "Gesendet", f"E-Mail an {to.strip()} gesendet.")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))
