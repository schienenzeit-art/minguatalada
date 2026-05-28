"""Bescheid/Brief-Wizard — Vorlagenauswahl, Fallsuche, PDF, E-Mail.

Öffnet sich aus TopBar-Dropdown oder aus der ClaimDetailPage-Toolbar.
Instantiiert fehlende Services automatisch (Lazy-Init).
"""
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTextEdit,
    QMessageBox, QGroupBox, QFrame, QSizePolicy,
)


class LetterWizardDialog(QDialog):
    """Wizard: Vorlage wählen → Fall suchen → PDF erstellen / E-Mail senden."""

    def __init__(
        self,
        template_type: str | None = None,
        claim_service=None,
        template_service=None,
        pdf_service=None,
        initial_claim: dict | None = None,   # optional: Fall direkt übergeben
        parent=None,
    ):
        super().__init__(parent)
        self._template_type    = template_type
        self._claim_service    = claim_service
        self._template_service = template_service
        self._pdf_service      = pdf_service
        self._claim: dict | None = initial_claim
        self._templates: list[dict] = []
        self._pdf_path: str | None = None

        # ── Lazy-Init fehlender Services ──────────────────────────────────────
        self._ensure_services()

        title = {
            "BESCHEID": "Bescheid erstellen",
            "BRIEF":    "Brief erstellen",
        }.get(template_type or "", "Dokument erstellen")
        self.setWindowTitle(title)
        self.setMinimumWidth(720)
        self.setMinimumHeight(600)

        flags = self.windowFlags() | Qt.WindowType.Window
        flags |= Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint
        self.setWindowFlags(flags)

        self._setup_ui()
        self._load_templates()

        # Wenn Fall direkt übergeben: Felder vorausfüllen
        if self._claim:
            self._prefill_from_claim()

    # ── Service-Initialisierung ───────────────────────────────────────────────
    def _ensure_services(self) -> None:
        """Instantiiert fehlende Services automatisch."""
        if self._template_service is None:
            from services.document_template_service import DocumentTemplateService
            self._template_service = DocumentTemplateService()
        if self._pdf_service is None:
            from services.pdf_service import PDFService
            self._pdf_service = PDFService()
        if self._claim_service is None:
            from services.claim_service import ClaimService
            self._claim_service = ClaimService()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        # ── 1. Vorlage wählen ─────────────────────────────────────────────────
        tpl_box = QGroupBox("1. Vorlage auswählen")
        tpl_layout = QVBoxLayout(tpl_box)
        tpl_layout.setSpacing(10)

        # Filter-Zeile
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        filter_row.addWidget(QLabel("Typ:"))
        self._type_filter = QComboBox()
        self._type_filter.setMaximumWidth(160)
        self._type_filter.addItem("Alle Typen", None)
        for key, label in [("BESCHEID", "Bescheid"), ("BRIEF", "Brief"),
                            ("FORMULAR", "Formular"), ("INFORMATION", "Information")]:
            self._type_filter.addItem(label, key)
        # Vorauswahl je nach übergebenem template_type
        if self._template_type:
            idx = self._type_filter.findData(self._template_type)
            if idx >= 0:
                self._type_filter.setCurrentIndex(idx)
        self._type_filter.currentIndexChanged.connect(self._apply_type_filter)
        filter_row.addWidget(self._type_filter)
        filter_row.addStretch()
        tpl_layout.addLayout(filter_row)

        # Haupt-Combo
        self._tpl_combo = QComboBox()
        self._tpl_combo.setMinimumHeight(34)
        self._tpl_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._tpl_combo.currentIndexChanged.connect(self._on_template_changed)
        tpl_layout.addWidget(self._tpl_combo)

        # Vorlage-Info (Name, Version, Status)
        self._tpl_info = QLabel("")
        self._tpl_info.setWordWrap(True)
        self._tpl_info.setStyleSheet("color: #555; font-size: 11px; padding: 4px 2px;")
        self._tpl_info.setVisible(False)
        tpl_layout.addWidget(self._tpl_info)

        # Warn-Banner falls keine Vorlagen
        self._no_tpl_banner = QLabel(
            "Keine aktiven Vorlagen vorhanden. "
            "Bitte zuerst im Admin-Bereich unter Dokumentvorlagen Vorlagen anlegen "
            "oder 'Standardvorlagen initialisieren' ausführen."
        )
        self._no_tpl_banner.setWordWrap(True)
        self._no_tpl_banner.setStyleSheet(
            "color: #9a6700; background: #fff7e6; border: 1px solid #f7d9a3; "
            "border-radius: 5px; padding: 8px 10px; font-size: 12px;"
        )
        self._no_tpl_banner.setVisible(False)
        tpl_layout.addWidget(self._no_tpl_banner)

        layout.addWidget(tpl_box)

        # ── 2. Fall zuordnen ──────────────────────────────────────────────────
        search_box = QGroupBox("2. Fall zuordnen (optional – für Merge-Felder)")
        search_layout = QVBoxLayout(search_box)
        search_layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        search_row.addWidget(QLabel("Aktenzeichen:"))
        self._case_input = QLineEdit()
        self._case_input.setPlaceholderText("z. B. AS-2025-000001")
        self._case_input.returnPressed.connect(self._search_claim)
        search_row.addWidget(self._case_input, 1)
        search_btn = QPushButton("Suchen")
        search_btn.setObjectName("SoftButton")
        search_btn.clicked.connect(self._search_claim)
        search_row.addWidget(search_btn)
        search_layout.addLayout(search_row)

        self._claim_info = QLabel("Kein Fall geladen – Platzhalter werden nicht ersetzt.")
        self._claim_info.setStyleSheet("color: #888; font-size: 11px;")
        self._claim_info.setWordWrap(True)
        search_layout.addWidget(self._claim_info)
        layout.addWidget(search_box)

        # ── 3. Vorschau ───────────────────────────────────────────────────────
        prev_box = QGroupBox("3. Vorschau")
        prev_layout = QVBoxLayout(prev_box)
        prev_layout.setContentsMargins(8, 8, 8, 8)
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setMinimumHeight(180)
        self._preview.setStyleSheet("font-size: 11px; background: #fafafa; font-family: 'Segoe UI', sans-serif;")
        prev_layout.addWidget(self._preview)

        refresh_btn = QPushButton("Vorschau aktualisieren")
        refresh_btn.setObjectName("SoftButton")
        refresh_btn.clicked.connect(self._update_preview)
        prev_row = QHBoxLayout()
        prev_row.addStretch()
        prev_row.addWidget(refresh_btn)
        prev_layout.addLayout(prev_row)
        layout.addWidget(prev_box)

        # ── Aktions-Buttons ───────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #ddd;")
        layout.addWidget(sep)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._pdf_btn = QPushButton("PDF erstellen & öffnen")
        self._pdf_btn.setObjectName("PrimaryButton")
        self._pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pdf_btn.clicked.connect(self._generate_pdf)
        btn_row.addWidget(self._pdf_btn)

        save_btn = QPushButton("PDF speichern …")
        save_btn.setObjectName("SoftButton")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save_pdf)
        btn_row.addWidget(save_btn)

        mail_btn = QPushButton("Per E-Mail senden")
        mail_btn.setObjectName("SecondaryButton")
        mail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mail_btn.clicked.connect(self._send_email)
        btn_row.addWidget(mail_btn)

        btn_row.addStretch()

        close_btn = QPushButton("Schließen")
        close_btn.setObjectName("SoftButton")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    # ── Vorlagen laden ────────────────────────────────────────────────────────
    def _load_templates(self) -> None:
        """Lädt alle aktiven Vorlagen und füllt die Combo."""
        self._all_templates: list[dict] = []
        try:
            self._all_templates = self._template_service.list_templates(include_inactive=False)
        except Exception as exc:
            self._show_no_templates(f"Fehler beim Laden der Vorlagen: {exc}")
            return

        self._apply_type_filter()

    def _apply_type_filter(self) -> None:
        """Filtert Vorlagen nach gewähltem Typ und befüllt Combo."""
        type_filter = self._type_filter.currentData()

        filtered = [
            t for t in self._all_templates
            if type_filter is None or t.get("template_type") == type_filter
        ]
        self._templates = filtered

        self._tpl_combo.blockSignals(True)
        self._tpl_combo.clear()

        if not filtered:
            self._tpl_combo.addItem("— Keine aktiven Vorlagen gefunden —", None)
            self._show_no_templates()
        else:
            self._no_tpl_banner.setVisible(False)
            for t in filtered:
                label = self._make_combo_label(t)
                self._tpl_combo.addItem(label, t["id"])

        self._tpl_combo.blockSignals(False)

        # Auto-Select: passende Vorlage für aktuellen Fall-Status
        self._auto_select_by_status()
        self._on_template_changed()

    @staticmethod
    def _make_combo_label(t: dict) -> str:
        """Erstellt einen informativen Combo-Eintrag."""
        from core.claim_status import ClaimStatus
        parts = [t["name"]]
        trigger = t.get("status_trigger")
        if trigger:
            status_label = ClaimStatus.get_display(trigger)
            parts.append(f"→ {status_label}")
        ttype = {
            "BESCHEID":    "Bescheid",
            "BRIEF":       "Brief",
            "INFORMATION": "Info",
            "FORMULAR":    "Formular",
        }.get(t.get("template_type", ""), t.get("template_type", ""))
        parts.append(f"[{ttype}]")
        ver = t.get("version")
        if ver and int(ver) > 1:
            parts.append(f"v{ver}")
        return "  ".join(parts)

    def _auto_select_by_status(self) -> None:
        """Wählt automatisch die Vorlage passend zum Claim-Status."""
        if not self._claim or not self._templates:
            return
        status = self._claim.get("status", "")
        for i, t in enumerate(self._templates):
            if t.get("status_trigger") == status:
                self._tpl_combo.setCurrentIndex(i)
                return

    def _on_template_changed(self) -> None:
        """Aktualisiert Info-Label und Vorschau wenn Vorlage geändert wird."""
        tpl_id = self._tpl_combo.currentData()
        if tpl_id is None:
            self._tpl_info.setVisible(False)
            return

        tpl = next((t for t in self._templates if t["id"] == tpl_id), None)
        if tpl:
            from core.claim_status import ClaimStatus
            trigger = tpl.get("status_trigger")
            status_info = f" · Status: {ClaimStatus.get_display(trigger)}" if trigger else ""
            desc = tpl.get("description") or ""
            ver = tpl.get("version") or 1
            updated = (tpl.get("updated_at") or "")[:10]
            info_parts = [f"Version {ver}"]
            if updated:
                info_parts.append(f"zuletzt geändert: {updated}")
            if desc:
                info_parts.append(desc)
            self._tpl_info.setText(f"{status_info.lstrip(' · ')}  ·  " + "  ·  ".join(info_parts)
                                   if status_info else "  ·  ".join(info_parts))
            self._tpl_info.setVisible(True)

        self._update_preview()

    def _show_no_templates(self, extra: str = "") -> None:
        txt = "Keine aktiven Vorlagen gefunden."
        if extra:
            txt += f" {extra}"
        txt += " → Admin-Bereich: Dokumentvorlagen → 'Standardvorlagen initialisieren'."
        self._no_tpl_banner.setText(txt)
        self._no_tpl_banner.setVisible(True)
        self._tpl_info.setVisible(False)

    # ── Fall suchen ───────────────────────────────────────────────────────────
    def _prefill_from_claim(self) -> None:
        """Füllt Felder aus einem bereits übergebenen Claim vor."""
        if not self._claim:
            return
        self._case_input.setText(self._claim.get("case_number", ""))
        from core.claim_status import ClaimStatus
        status = ClaimStatus.get_display(self._claim.get("status", ""))
        name = (f"{self._claim.get('person_first_name','')} "
                f"{self._claim.get('person_last_name','')}").strip()
        self._claim_info.setText(
            f"Fall geladen: {self._claim.get('case_number')} · {name} · Status: {status}"
        )
        self._claim_info.setStyleSheet("color: #1a8f4a; font-size: 11px;")
        self._auto_select_by_status()
        self._update_preview()

    def _search_claim(self) -> None:
        case_number = self._case_input.text().strip()
        if not case_number:
            return
        try:
            claims = self._claim_service.list_claims()
            found = next(
                (c for c in claims
                 if c.get("case_number", "").lower() == case_number.lower()),
                None,
            )
            if found:
                self._claim = self._claim_service.get_claim_by_id(found["id"])
                from core.claim_status import ClaimStatus
                status = ClaimStatus.get_display(self._claim.get("status", ""))
                name = (f"{self._claim.get('person_first_name','')} "
                        f"{self._claim.get('person_last_name','')}").strip()
                self._claim_info.setText(
                    f"Fall: {self._claim.get('case_number')} · {name} · Status: {status}"
                )
                self._claim_info.setStyleSheet("color: #1a8f4a; font-size: 11px;")
                self._auto_select_by_status()
                self._update_preview()
            else:
                self._claim_info.setText(
                    f"Kein Fall mit Aktenzeichen '{case_number}' gefunden."
                )
                self._claim_info.setStyleSheet("color: #c0362a; font-size: 11px;")
        except Exception as exc:
            self._claim_info.setText(f"Fehler: {exc}")

    # ── Kontext + Vorschau ────────────────────────────────────────────────────
    def _get_context(self) -> dict:
        if self._claim:
            from services.document_template_service import build_claim_context
            return build_claim_context(self._claim)
        return {"DATUM": date.today().strftime("%d.%m.%Y")}

    def _update_preview(self) -> None:
        tpl_id = self._tpl_combo.currentData()
        if tpl_id is None:
            self._preview.setPlaceholderText("Vorlage auswählen um Vorschau anzuzeigen …")
            self._preview.clear()
            return
        try:
            rendered = self._template_service.render(tpl_id, self._get_context())
            self._preview.setPlainText(rendered)
        except Exception as exc:
            self._preview.setPlainText(f"Vorschau-Fehler: {exc}")

    # ── PDF-Aktionen ──────────────────────────────────────────────────────────
    def _get_tpl_id(self) -> int | None:
        tpl_id = self._tpl_combo.currentData()
        if tpl_id is None:
            QMessageBox.warning(self, "Vorlage fehlt",
                                "Bitte zuerst eine Vorlage auswählen.")
        return tpl_id

    def _generate_pdf(self) -> None:
        tpl_id = self._get_tpl_id()
        if tpl_id is None:
            return
        try:
            path = self._pdf_service.generate_letter_pdf(tpl_id, self._get_context())
            self._pdf_path = path
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))

    def _save_pdf(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        tpl_id = self._get_tpl_id()
        if tpl_id is None:
            return
        default = "Bescheid.pdf"
        if self._claim:
            cn = self._claim.get("case_number", "").replace("/", "_")
            default = f"Bescheid_{cn}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "PDF speichern", default, "PDF (*.pdf)")
        if not path:
            return
        try:
            self._pdf_service.generate_letter_pdf(tpl_id, self._get_context(), file_path=path)
            self._pdf_path = path
            QMessageBox.information(self, "Gespeichert", f"PDF gespeichert:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))

    def _send_email(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        tpl_id = self._get_tpl_id()
        if tpl_id is None:
            return
        email = (self._claim or {}).get("person_email", "") or ""
        to, ok = QInputDialog.getText(self, "E-Mail senden", "Empfänger:", text=email)
        if not ok or not to.strip():
            return
        ctx = self._get_context()
        try:
            if not self._pdf_path:
                self._pdf_path = self._pdf_service.generate_letter_pdf(tpl_id, ctx)
            from services.user_mail_service import UserMailService
            name = f"{ctx.get('VORNAME','')} {ctx.get('NACHNAME','')}".strip()
            UserMailService().send_document_mail(
                to_email=to.strip(), person_name=name,
                subject=None, html_body=None,
                pdf_paths=[self._pdf_path],
            )
            QMessageBox.information(self, "Gesendet", f"E-Mail an {to.strip()} gesendet.")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))
