"""Serienbriefe – Batch-PDF-Generierung für mehrere Fälle/Personen.

Zugänglich über Admin-Bereich und Topbar-Dropdown.
"""
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QCheckBox, QProgressBar, QGroupBox, QFileDialog,
    QAbstractItemView,
)
from ui.components.page_header import PageHeader


class SerialLettersPage(QWidget):
    """Einbettbare Seite für den Admin-Bereich."""

    def __init__(self, claim_service=None, template_service=None, pdf_service=None, parent=None):
        super().__init__(parent)
        self._claim_service    = claim_service
        self._template_service = template_service
        self._pdf_service      = pdf_service
        self._claims: list[dict] = []
        self._templates: list[dict] = []
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            title="Serienbriefe",
            subtitle="Vorlage wählen, Fälle auswählen und Briefe als Sammel-PDF oder Einzel-PDFs generieren.",
        ))

        # ── Vorlage + Typ ─────────────────────────────────────────────────────
        opt_row = QHBoxLayout()
        opt_row.setSpacing(12)
        opt_row.addWidget(QLabel("Vorlage:"))
        self._tpl_combo = QComboBox()
        self._tpl_combo.setMinimumWidth(280)
        opt_row.addWidget(self._tpl_combo)
        opt_row.addWidget(QLabel("Status-Filter:"))
        self._status_combo = QComboBox()
        self._status_combo.addItem("Alle Status", None)
        from core.claim_status import ClaimStatus
        for key, label in ClaimStatus.DISPLAY_NAMES.items():
            self._status_combo.addItem(label, key)
        self._status_combo.currentIndexChanged.connect(self._apply_filter)
        opt_row.addWidget(self._status_combo)
        opt_row.addStretch()
        layout.addLayout(opt_row)

        # ── Tabelle ───────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["", "Aktenzeichen", "Person", "Status", "Standort"])
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setColumnWidth(0, 36)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

        # ── Auswahl-Aktionen ──────────────────────────────────────────────────
        sel_row = QHBoxLayout()
        sel_all = QPushButton("Alle auswählen")
        sel_all.setObjectName("SoftButton")
        sel_all.clicked.connect(self._select_all)
        sel_none = QPushButton("Auswahl aufheben")
        sel_none.setObjectName("SoftButton")
        sel_none.clicked.connect(self._select_none)
        self._sel_lbl = QLabel("0 ausgewählt")
        self._sel_lbl.setStyleSheet("color: #666; font-size: 11px;")
        sel_row.addWidget(sel_all)
        sel_row.addWidget(sel_none)
        sel_row.addWidget(self._sel_lbl)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        # ── Fortschritt ───────────────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setMaximumHeight(8)
        self._progress.hide()
        layout.addWidget(self._progress)

        # ── Aktionen ──────────────────────────────────────────────────────────
        act_row = QHBoxLayout()
        batch_btn = QPushButton("Sammel-PDF generieren")
        batch_btn.setObjectName("PrimaryButton")
        batch_btn.clicked.connect(self._generate_batch)
        single_btn = QPushButton("Einzel-PDFs generieren")
        single_btn.setObjectName("SecondaryButton")
        single_btn.clicked.connect(self._generate_single)
        act_row.addWidget(batch_btn)
        act_row.addWidget(single_btn)
        act_row.addStretch()
        layout.addLayout(act_row)

    def _load_data(self):
        # Vorlagen laden
        if self._template_service:
            try:
                self._templates = self._template_service.list_templates(include_inactive=False)
                self._tpl_combo.clear()
                for t in self._templates:
                    self._tpl_combo.addItem(f"{t['name']} [{t.get('template_type','')}]", t["id"])
            except Exception:
                pass

        # Fälle laden
        if self._claim_service:
            try:
                self._claims = self._claim_service.list_claims()
            except Exception:
                self._claims = []
        self._apply_filter()

    def _apply_filter(self):
        from core.claim_status import ClaimStatus
        status_filter = self._status_combo.currentData()
        filtered = [
            c for c in self._claims
            if status_filter is None or c.get("status") == status_filter
        ]
        self._table.setRowCount(len(filtered))
        for row, claim in enumerate(filtered):
            cb = QCheckBox()
            cb.stateChanged.connect(self._update_count)
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.setContentsMargins(6, 0, 0, 0)
            cb_layout.addWidget(cb)
            self._table.setCellWidget(row, 0, cb_widget)
            self._table.setItem(row, 1, QTableWidgetItem(claim.get("case_number", "")))
            name = f"{claim.get('person_first_name','')} {claim.get('person_last_name','')}".strip()
            self._table.setItem(row, 2, QTableWidgetItem(name))
            self._table.setItem(row, 3, QTableWidgetItem(
                ClaimStatus.get_display(claim.get("status", ""))))
            self._table.setItem(row, 4, QTableWidgetItem(claim.get("location_name", "")))
            self._table.item(row, 1).setData(Qt.ItemDataRole.UserRole, claim.get("id"))
        self._update_count()

    def _update_count(self):
        count = sum(1 for row in range(self._table.rowCount())
                    if self._get_row_checkbox(row) and self._get_row_checkbox(row).isChecked())
        self._sel_lbl.setText(f"{count} ausgewählt")

    def _get_row_checkbox(self, row: int) -> QCheckBox | None:
        w = self._table.cellWidget(row, 0)
        if w:
            for child in w.children():
                if isinstance(child, QCheckBox):
                    return child
        return None

    def _select_all(self):
        for row in range(self._table.rowCount()):
            cb = self._get_row_checkbox(row)
            if cb:
                cb.setChecked(True)

    def _select_none(self):
        for row in range(self._table.rowCount()):
            cb = self._get_row_checkbox(row)
            if cb:
                cb.setChecked(False)

    def _selected_claim_ids(self) -> list[int]:
        ids = []
        for row in range(self._table.rowCount()):
            cb = self._get_row_checkbox(row)
            if cb and cb.isChecked():
                item = self._table.item(row, 1)
                if item:
                    ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    def _get_contexts(self, claim_ids: list[int]) -> list[dict]:
        from services.document_template_service import build_claim_context
        contexts = []
        for cid in claim_ids:
            try:
                claim = self._claim_service.get_claim_by_id(cid)
                if claim:
                    contexts.append(build_claim_context(claim))
            except Exception:
                pass
        return contexts

    def _generate_batch(self):
        tpl_id = self._tpl_combo.currentData()
        if tpl_id is None:
            QMessageBox.warning(self, "Hinweis", "Bitte eine Vorlage auswählen.")
            return
        ids = self._selected_claim_ids()
        if not ids:
            QMessageBox.warning(self, "Hinweis", "Bitte mindestens einen Fall auswählen.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Sammel-PDF speichern", f"Serienbriefe_{date.today()}.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            contexts = self._get_contexts(ids)
            self._pdf_service.generate_serial_letters_pdf(tpl_id, contexts, file_path=path)
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            QMessageBox.information(self, "Fertig", f"Sammel-PDF mit {len(contexts)} Brief(en) erstellt.")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))

    def _generate_single(self):
        tpl_id = self._tpl_combo.currentData()
        if tpl_id is None:
            QMessageBox.warning(self, "Hinweis", "Bitte eine Vorlage auswählen.")
            return
        ids = self._selected_claim_ids()
        if not ids:
            QMessageBox.warning(self, "Hinweis", "Bitte mindestens einen Fall auswählen.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Zielordner wählen")
        if not folder:
            return
        self._progress.setMaximum(len(ids))
        self._progress.setValue(0)
        self._progress.show()
        ok_count = 0
        for i, cid in enumerate(ids):
            try:
                claim = self._claim_service.get_claim_by_id(cid)
                if claim:
                    from services.document_template_service import build_claim_context
                    ctx  = build_claim_context(claim)
                    path = f"{folder}/Brief_{claim.get('case_number','Fall').replace('/','_')}.pdf"
                    self._pdf_service.generate_letter_pdf(tpl_id, ctx, file_path=path)
                    ok_count += 1
            except Exception:
                pass
            self._progress.setValue(i + 1)
        self._progress.hide()
        QMessageBox.information(self, "Fertig", f"{ok_count} Einzel-PDF(s) in:\n{folder}")


class SerialLettersDialog(QDialog):
    """Als Dialog aus der Topbar öffenbar."""

    def __init__(self, claim_service=None, template_service=None, pdf_service=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Serienbriefe")
        self.setMinimumSize(900, 640)
        flags = self.windowFlags() | Qt.WindowType.Window
        flags |= Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint
        self.setWindowFlags(flags)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(SerialLettersPage(
            claim_service=claim_service,
            template_service=template_service,
            pdf_service=pdf_service,
            parent=self,
        ))
