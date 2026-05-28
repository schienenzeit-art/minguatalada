"""
M3 – Bescheid-/Dokumentvorlagen
Erstellen, bearbeiten und generieren von Text-Vorlagen mit Platzhaltern.
"""

from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QComboBox,
    QCheckBox, QSplitter, QFrame, QDialogButtonBox, QScrollArea,
)
from ui.components.page_header import PageHeader
from services.document_template_service import DocumentTemplateService, TEMPLATE_TYPES
from services.category_service import CategoryService
from core.claim_status import ClaimStatus


_TYPE_LABELS = {
    "BRIEF":       "Brief",
    "BESCHEID":    "Bescheid",
    "FORMULAR":    "Formular",
    "INFORMATION": "Information",
}


class DocumentTemplatesPage(QWidget):
    def __init__(
        self,
        template_service: DocumentTemplateService | None = None,
        category_service: CategoryService | None = None,
    ):
        super().__init__()
        self.svc     = template_service or DocumentTemplateService()
        self.cat_svc = category_service or CategoryService()
        self._templates: list[dict] = []
        self._categories: list[dict] = []
        self._setup_ui()
        self._load_categories()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            title="Dokumentvorlagen",
            subtitle="Brief-, Bescheid- und Formularvorlagen mit Platzhaltern erstellen und verwalten.",
        ))

        # ── Info: Platzhalter-Hilfe ────────────────────────────────────────────
        info = QFrame()
        info.setObjectName("Card")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(12, 8, 12, 8)
        ph_text = " · ".join(f"{{{{{k}}}}}" for k in [
            "VORNAME", "NACHNAME", "ADRESSE", "PLZ", "ORT",
            "AKTENZEICHEN", "DATUM", "STANDORT", "MITARBEITER"
        ])
        info_lbl = QLabel(f"<b>Verfügbare Platzhalter:</b> {ph_text}")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("font-size: 11px; color: #4a4845;")
        info_layout.addWidget(info_lbl)
        layout.addWidget(info)

        # ── Toolbar ────────────────────────────────────────────────────────────
        tool_row = QHBoxLayout()
        tool_row.addStretch()
        new_btn = QPushButton("+ Neue Vorlage")
        new_btn.setObjectName("PrimaryButton")
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.clicked.connect(self._new_template)
        tool_row.addWidget(new_btn)
        layout.addLayout(tool_row)

        # ── Tabelle + Vorschau (Splitter) ──────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Tabelle
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Name", "Typ", "Kategorie", "Aktiv"])
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.currentItemChanged.connect(
            lambda cur, prev: self._on_row_changed(cur.row() if cur else -1)
        )
        self._table.doubleClicked.connect(self._edit_selected)
        splitter.addWidget(self._table)

        # Vorschau
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(8, 0, 0, 0)
        preview_layout.addWidget(QLabel("<b>Vorschau</b>"))
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setStyleSheet(
            "font-family: 'Segoe UI', sans-serif; font-size: 13px; "
            "background: #fafafa; border: 1px solid #ececec;"
        )
        preview_layout.addWidget(self._preview)
        splitter.addWidget(preview_widget)

        splitter.setSizes([380, 420])
        layout.addWidget(splitter)

        # ── Buttons ────────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #9b9896; font-size: 12px;")
        btn_row.addWidget(self._status_lbl, 1)

        edit_btn = QPushButton("Bearbeiten")
        edit_btn.setObjectName("SoftButton")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(self._edit_selected)
        btn_row.addWidget(edit_btn)

        generate_btn = QPushButton("Dokument generieren")
        generate_btn.setObjectName("PrimaryButton")
        generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        generate_btn.clicked.connect(self._generate_selected)
        btn_row.addWidget(generate_btn)

        docx_up_btn = QPushButton("DOCX hochladen")
        docx_up_btn.setObjectName("SoftButton")
        docx_up_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        docx_up_btn.setToolTip(
            "Word-Vorlage (.docx) hochladen. Platzhalter: {{VORNAME}}, {{STATUS}}, ..."
        )
        docx_up_btn.clicked.connect(self._upload_docx)
        btn_row.addWidget(docx_up_btn)

        docx_down_btn = QPushButton("DOCX herunterladen")
        docx_down_btn.setObjectName("SoftButton")
        docx_down_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        docx_down_btn.clicked.connect(self._download_docx)
        btn_row.addWidget(docx_down_btn)

        delete_btn = QPushButton("Löschen")
        delete_btn.setObjectName("DangerButton")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(delete_btn)

        layout.addLayout(btn_row)

    def _load_categories(self):
        try:
            self._categories = self.cat_svc.list_categories()
        except Exception:
            self._categories = []

    def refresh(self):
        self._templates = self.svc.list_templates(include_inactive=True)
        self._table.setRowCount(len(self._templates))
        for i, t in enumerate(self._templates):
            self._table.setItem(i, 0, QTableWidgetItem(t["name"]))
            self._table.setItem(i, 1, QTableWidgetItem(_TYPE_LABELS.get(t["template_type"], t["template_type"])))
            self._table.setItem(i, 2, QTableWidgetItem(t.get("category_name") or "—"))
            active = QTableWidgetItem("✓" if t.get("is_active") else "—")
            active.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 3, active)
        self._status_lbl.setText(f"{len(self._templates)} Vorlage(n) vorhanden.")

    def _on_row_changed(self, row: int):
        if row < 0 or row >= len(self._templates):
            self._preview.clear()
            return
        tpl = self._templates[row]
        body = tpl.get("body_text") or "(kein Inhalt)"
        # Show with sample substitution
        sample = self.svc.render(tpl["id"], {
            "VORNAME":      "Max",
            "NACHNAME":     "Mustermann",
            "ADRESSE":      "Musterstraße 1",
            "PLZ":          "6700",
            "ORT":          "Bludenz",
            "AKTENZEICHEN": "AS-2025-000001",
            "DATUM":        date.today().strftime("%d.%m.%Y"),
            "STANDORT":     "Bludenz",
            "MITARBEITER":  "Maria Muster",
        })
        self._preview.setPlainText(sample)

    def _get_selected_row(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def _new_template(self):
        dlg = _TemplateDialog(categories=self._categories, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.svc.create_template(dlg.get_data())
                self.refresh()
            except Exception as exc:
                QMessageBox.warning(self, "Fehler", str(exc))

    def _edit_selected(self):
        row = self._get_selected_row()
        if row is None:
            QMessageBox.information(self, "Hinweis", "Bitte eine Vorlage auswählen.")
            return
        tpl = self._templates[row]
        dlg = _TemplateDialog(categories=self._categories, template=tpl, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.svc.update_template(tpl["id"], dlg.get_data())
                self.refresh()
            except Exception as exc:
                QMessageBox.warning(self, "Fehler", str(exc))

    def _delete_selected(self):
        row = self._get_selected_row()
        if row is None:
            QMessageBox.information(self, "Hinweis", "Bitte eine Vorlage auswählen.")
            return
        tpl = self._templates[row]
        ans = QMessageBox.question(
            self, "Vorlage löschen",
            f"Vorlage «{tpl['name']}» löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.svc.delete_template(tpl["id"])
            self.refresh()

    def _generate_selected(self):
        row = self._get_selected_row()
        if row is None:
            QMessageBox.information(self, "Hinweis", "Bitte eine Vorlage auswählen.")
            return
        tpl = self._templates[row]
        dlg = _GenerateDialog(template=tpl, svc=self.svc, parent=self)
        dlg.exec()

    def _upload_docx(self):
        row = self._get_selected_row()
        if row is None:
            QMessageBox.information(self, "Hinweis", "Bitte eine Vorlage auswählen.")
            return
        tpl = self._templates[row]
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "DOCX-Vorlage öffnen", "", "Word-Dokument (*.docx)"
        )
        if not path:
            return
        try:
            with open(path, "rb") as f:
                docx_bytes = f.read()
            self.svc.upload_docx(tpl["id"], docx_bytes)
            QMessageBox.information(self, "Hochgeladen",
                f"DOCX-Vorlage «{tpl['name']}» wurde erfolgreich hochgeladen.\n"
                "Platzhalter {{VORNAME}}, {{NACHNAME}}, {{STATUS}} etc. werden beim Generieren ersetzt.")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))

    def _download_docx(self):
        row = self._get_selected_row()
        if row is None:
            QMessageBox.information(self, "Hinweis", "Bitte eine Vorlage auswählen.")
            return
        tpl = self._templates[row]
        docx_bytes = self.svc.get_docx_bytes(tpl["id"])
        if not docx_bytes:
            QMessageBox.information(self, "Keine DOCX",
                "Diese Vorlage hat keine hochgeladene DOCX-Datei.\n"
                "Klicken Sie 'DOCX hochladen' um eine Word-Vorlage hinzuzufügen.")
            return
        from PyQt6.QtWidgets import QFileDialog
        safe_name = tpl["name"].replace(" ", "_").replace("/", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "DOCX speichern", f"{safe_name}.docx", "Word-Dokument (*.docx)"
        )
        if not path:
            return
        with open(path, "wb") as f:
            f.write(bytes(docx_bytes))
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        QMessageBox.information(self, "Heruntergeladen", f"Vorlage gespeichert:\n{path}")


class _TemplateDialog(QDialog):
    def __init__(self, categories: list[dict],
                 template: dict | None = None, parent=None):
        super().__init__(parent)
        self._template = template
        self._categories = categories
        self.setWindowTitle("Vorlage bearbeiten" if template else "Neue Vorlage")
        self.setMinimumWidth(640)
        self.setMinimumHeight(520)
        self._setup_ui()
        if template:
            self._fill(template)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setSpacing(8)

        self._name = QLineEdit()
        form.addRow("Name *", self._name)

        self._type_combo = QComboBox()
        for t in TEMPLATE_TYPES:
            self._type_combo.addItem(_TYPE_LABELS.get(t, t), t)
        form.addRow("Typ", self._type_combo)

        self._cat_combo = QComboBox()
        self._cat_combo.addItem("(keine Kategorie)", None)
        for c in self._categories:
            self._cat_combo.addItem(c["name"], c["id"])
        form.addRow("Kategorie", self._cat_combo)

        self._description = QLineEdit()
        self._description.setPlaceholderText("Kurze Beschreibung …")
        form.addRow("Beschreibung", self._description)

        self._active_cb = QCheckBox("Vorlage aktiv")
        self._active_cb.setChecked(True)
        form.addRow("", self._active_cb)

        self._status_trigger = QComboBox()
        self._status_trigger.addItem("(kein Status-Trigger)", None)
        for key, label in ClaimStatus.DISPLAY_NAMES.items():
            self._status_trigger.addItem(label, key)
        form.addRow("Standard für Status", self._status_trigger)

        layout.addLayout(form)

        layout.addWidget(QLabel("Inhalt (Platzhalter: {{VORNAME}}, {{NACHNAME}}, {{AKTENZEICHEN}}, …):"))
        self._body = QTextEdit()
        self._body.setMinimumHeight(250)
        self._body.setPlaceholderText(
            "Hier den Vorlagentext eingeben.\n"
            "Platzhalter werden beim Generieren durch echte Werte ersetzt.\n\n"
            "Beispiel:\nSehr geehrte/r {{VORNAME}} {{NACHNAME}},\n\n"
            "Ihr Antrag (Aktenzeichen: {{AKTENZEICHEN}}) wurde bearbeitet …"
        )
        layout.addWidget(self._body)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _fill(self, t: dict):
        self._name.setText(t.get("name", ""))
        idx = self._type_combo.findData(t.get("template_type", "BRIEF"))
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        idx = self._cat_combo.findData(t.get("category_id"))
        if idx >= 0:
            self._cat_combo.setCurrentIndex(idx)
        self._description.setText(t.get("description") or "")
        self._active_cb.setChecked(bool(t.get("is_active", 1)))
        self._body.setPlainText(t.get("body_text") or "")
        st_idx = self._status_trigger.findData(t.get("status_trigger"))
        if st_idx >= 0:
            self._status_trigger.setCurrentIndex(st_idx)

    def _on_save(self):
        if not self._name.text().strip():
            QMessageBox.warning(self, "Fehler", "Name ist Pflichtfeld.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name":           self._name.text().strip(),
            "template_type":  self._type_combo.currentData(),
            "category_id":    self._cat_combo.currentData(),
            "description":    self._description.text().strip() or None,
            "is_active":      self._active_cb.isChecked(),
            "body_text":      self._body.toPlainText(),
            "status_trigger": self._status_trigger.currentData(),
        }


class _GenerateDialog(QDialog):
    def __init__(self, template: dict, svc: DocumentTemplateService, parent=None):
        super().__init__(parent)
        self._template = template
        self.svc = svc
        self.setWindowTitle(f"Dokument generieren: {template['name']}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(560)
        self._context: dict[str, QLineEdit] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Platzhalter-Eingaben
        placeholders = self.svc.extract_placeholders(self._template.get("body_text", ""))
        default_vals = {
            "DATUM": date.today().strftime("%d.%m.%Y"),
        }

        if placeholders:
            layout.addWidget(QLabel("<b>Platzhalter ausfüllen:</b>"))
            form = QFormLayout()
            form.setSpacing(6)
            for ph in sorted(placeholders):
                inp = QLineEdit()
                inp.setPlaceholderText(self.svc.get_placeholders().get(ph, ""))
                inp.setText(default_vals.get(ph, ""))
                form.addRow(ph, inp)
                self._context[ph] = inp
            layout.addLayout(form)
        else:
            layout.addWidget(QLabel("Diese Vorlage enthält keine Platzhalter."))

        # Vorschau
        layout.addWidget(QLabel("<b>Vorschau:</b>"))
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setStyleSheet("font-size: 13px; background: #fafafa;")
        layout.addWidget(self._preview)

        btn_row = QHBoxLayout()
        preview_btn = QPushButton("Vorschau aktualisieren")
        preview_btn.setObjectName("SoftButton")
        preview_btn.clicked.connect(self._update_preview)
        btn_row.addWidget(preview_btn)
        btn_row.addStretch()
        copy_btn = QPushButton("Text kopieren")
        copy_btn.setObjectName("SoftButton")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(copy_btn)
        pdf_btn = QPushButton("Als PDF speichern")
        pdf_btn.setObjectName("PrimaryButton")
        pdf_btn.clicked.connect(self._save_as_pdf)
        btn_row.addWidget(pdf_btn)
        mail_btn = QPushButton("Per E-Mail senden")
        mail_btn.setObjectName("SecondaryButton")
        mail_btn.clicked.connect(self._send_by_email)
        btn_row.addWidget(mail_btn)
        close_btn = QPushButton("Schließen")
        close_btn.setObjectName("SoftButton")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._update_preview()

    def _get_context(self) -> dict:
        return {k: v.text() for k, v in self._context.items()}

    def _update_preview(self):
        rendered = self.svc.render(self._template["id"], self._get_context())
        self._preview.setPlainText(rendered)

    def _copy_to_clipboard(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._preview.toPlainText())
        QMessageBox.information(self, "Kopiert", "Text in Zwischenablage kopiert.")

    def _save_as_pdf(self):
        from PyQt6.QtWidgets import QFileDialog
        from services.pdf_service import PDFService
        path, _ = QFileDialog.getSaveFileName(
            self, "PDF speichern", f"{self._template['name']}.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            pdf_svc = PDFService()
            pdf_svc.generate_letter_pdf(self._template["id"], self._get_context(), file_path=path)
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"PDF-Erstellung fehlgeschlagen:\n{exc}")

    def _send_by_email(self):
        from PyQt6.QtWidgets import QInputDialog
        to, ok = QInputDialog.getText(self, "E-Mail senden", "Empfänger-E-Mail-Adresse:")
        if not ok or not to.strip():
            return
        try:
            from services.pdf_service import PDFService
            from services.mail_service import MailService
            pdf_svc  = PDFService()
            pdf_path = pdf_svc.generate_letter_pdf(self._template["id"], self._get_context())
            mail_svc = MailService()
            name = f"{self._get_context().get('VORNAME','')} {self._get_context().get('NACHNAME','')}".strip()
            mail_svc.send_letter(to_email=to.strip(), person_name=name or "Empfänger", pdf_path=pdf_path)
            QMessageBox.information(self, "Gesendet", f"E-Mail an {to.strip()} wurde gesendet.")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"E-Mail konnte nicht gesendet werden:\n{exc}")
