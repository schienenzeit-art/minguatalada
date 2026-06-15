from pathlib import Path

from PyQt6.QtCore import Qt, QUrl, QDate
from PyQt6.QtGui import QDesktopServices, QColor
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QGroupBox,
    QPushButton,
    QComboBox,
    QLineEdit,
    QDateEdit,
    QListWidget,
    QMessageBox,
    QFileDialog,
    QScrollArea,
    QSizePolicy,
    QTableWidgetItem,
    QHeaderView,
    QWidget,
    QFrame,
    QTabWidget,
    QTextEdit,
)

from ui.components.table_widget import TableWidget
from core.claim_status import ClaimStatus
from core.document_status import DocumentStatus
from core.session import Session
from services.claim_service import ClaimService
from services.document_service import DocumentService
from services.pdf_service import PDFService
from services.person_note_service import PersonNoteService
from services.service_factory import make_claim_service, make_pdf_service
from database.repositories.person_repository import PersonRepository


class PersonDossierDialog(QDialog):
    def __init__(
        self,
        person_id: int,
        claim_service: ClaimService | None = None,
        document_service: DocumentService | None = None,
        pdf_service: PDFService | None = None,
        person_note_service: PersonNoteService | None = None,
    ):
        super().__init__()
        self.person_id = person_id
        self.claim_service = claim_service or make_claim_service()
        self.document_service = document_service or DocumentService()
        self.pdf_service = pdf_service or make_pdf_service()
        self.person_note_service = person_note_service or PersonNoteService()
        self.person_repository = PersonRepository()
        self.selected_files: list[str] = []
        self._person: dict = {}
        self._all_claims: list[dict] = []

        self.setWindowTitle("Personendossier")
        self.setMinimumSize(1020, 740)
        flags = self.windowFlags()
        flags |= Qt.WindowType.Window
        flags |= Qt.WindowType.WindowMinimizeButtonHint
        flags |= Qt.WindowType.WindowMaximizeButtonHint
        self.setWindowFlags(flags)

        self.setup_ui()
        self.load_person()
        self.load_claims()
        self.refresh_documents()
        self.load_activity_feed()
        self._load_person_notes()

    # ─────────────────────────────────────────────────────────────────────────
    def setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setSpacing(16)
        main.setContentsMargins(12, 12, 12, 12)

        # ── Kopfzeile ────────────────────────────────────────────────────────
        title = QLabel("Personendossier")
        title.setObjectName("PageTitle")
        self.subtitle_lbl = QLabel("Persönliche Daten, Fälle, Dokumente, Aktivitätenchronik")
        self.subtitle_lbl.setObjectName("PageSubtitle")
        self.subtitle_lbl.setWordWrap(True)
        main.addWidget(title)
        main.addWidget(self.subtitle_lbl)

        # ── Tab-Widget ────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tabs.addTab(self._build_person_tab(),    "Stammdaten")
        self.tabs.addTab(self._build_claims_tab(),    "Fälle")
        self.tabs.addTab(self._build_documents_tab(), "Dokumente")
        self.tabs.addTab(self._build_activity_tab(),  "Aktivitäten")
        self.tabs.addTab(self._build_notes_tab(),     "Notizen")

        main.addWidget(self.tabs)

        # ── Aktionsleiste ─────────────────────────────────────────────────────
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        self.edit_button  = QPushButton("Person bearbeiten")
        self.edit_button.setObjectName("SoftButton")
        self.edit_button.clicked.connect(self.on_edit_person)
        self.print_button = QPushButton("Dossier drucken")
        self.print_button.setObjectName("PrimaryButton")
        self.print_button.clicked.connect(self.on_print_dossier)
        close_button = QPushButton("Schließen")
        close_button.clicked.connect(self.reject)
        action_layout.addWidget(self.edit_button)
        action_layout.addWidget(self.print_button)
        action_layout.addWidget(close_button)
        main.addLayout(action_layout)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── Tab 1: Stammdaten ─────────────────────────────────────────────────────
    def _build_person_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        box = QGroupBox("Personendaten")
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(10)

        self.name_label      = QLabel("-")
        self.birthdate_label = QLabel("-")
        self.address_label   = QLabel("-")
        self.city_label      = QLabel("-")
        self.email_label     = QLabel("-")
        self.category_label  = QLabel("-")
        self.location_label  = QLabel("-")

        for lbl in [self.name_label, self.birthdate_label, self.address_label,
                    self.city_label, self.email_label, self.category_label, self.location_label]:
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 13px; color: #1a1917;")

        form.addRow("Name:",           self.name_label)
        form.addRow("Geburtsdatum:",   self.birthdate_label)
        form.addRow("Adresse:",        self.address_label)
        form.addRow("Ort:",            self.city_label)
        form.addRow("E-Mail:",         self.email_label)
        form.addRow("Kategorie:",      self.category_label)
        form.addRow("Standort:",       self.location_label)
        box.setLayout(form)
        layout.addWidget(box)
        layout.addStretch()
        return w

    # ── Tab 2: Fälle ─────────────────────────────────────────────────────────
    def _build_claims_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.claims_search = QLineEdit()
        self.claims_search.setPlaceholderText("Nach Fallnummer, Status oder Kategorie suchen …")
        self.claims_search.textChanged.connect(self._filter_claims_table)

        self.claims_table = TableWidget(6)
        self.claims_table.setHorizontalHeaderLabels([
            "Fallnummer", "Status", "Kategorie", "Standort", "Erstellt", "Wiedervorlage"
        ])
        self.claims_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.claims_table.setMinimumHeight(180)
        self.claims_table.verticalHeader().hide()
        self.claims_table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.claims_table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.claims_table.cellDoubleClicked.connect(self._open_claim_from_table)

        layout.addWidget(self.claims_search)
        layout.addWidget(self.claims_table)
        return w

    # ── Tab 3: Dokumente ──────────────────────────────────────────────────────
    def _build_documents_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        upload_form = QFormLayout()
        upload_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        upload_form.setHorizontalSpacing(20)
        upload_form.setVerticalSpacing(8)

        self.document_type_combo = QComboBox()
        self.document_description_input = QLineEdit()
        self.document_description_input.setPlaceholderText("Beschreibung (optional)")
        for dt in self.document_service.list_document_types():
            self.document_type_combo.addItem(dt["name"], dt["id"])
        upload_form.addRow("Dokumenttyp:", self.document_type_combo)
        upload_form.addRow("Beschreibung:", self.document_description_input)

        upload_buttons = QHBoxLayout()
        self.choose_files_button = QPushButton("Dateien auswählen")
        self.choose_files_button.clicked.connect(self.on_select_files)
        self.clear_files_button = QPushButton("Auswahl löschen")
        self.clear_files_button.clicked.connect(self.on_clear_files)
        self.upload_files_button = QPushButton("Hochladen")
        self.upload_files_button.setObjectName("PrimaryButton")
        self.upload_files_button.clicked.connect(self.on_upload_files)
        upload_buttons.addWidget(self.choose_files_button)
        upload_buttons.addWidget(self.clear_files_button)
        upload_buttons.addWidget(self.upload_files_button)
        upload_buttons.addStretch()

        self.file_list_widget = QListWidget()
        self.file_list_widget.setFixedHeight(72)

        self.documents_table = TableWidget(7)
        self.documents_table.setHorizontalHeaderLabels([
            "Titel", "Typ", "Fall", "Hochgeladen", "Status", "Öffnen", "Löschen",
        ])
        self.documents_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.documents_table.verticalHeader().hide()
        self.documents_table.setSelectionBehavior(self.documents_table.SelectionBehavior.SelectRows)
        self.documents_table.setEditTriggers(self.documents_table.EditTrigger.NoEditTriggers)
        self.documents_table.setMinimumHeight(160)

        layout.addLayout(upload_form)
        layout.addLayout(upload_buttons)
        layout.addWidget(self.file_list_widget)
        layout.addWidget(self.documents_table)
        return w

    # ── Tab 4: Aktivitätenchronik ─────────────────────────────────────────────
    def _build_activity_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header_lbl = QLabel("Vollständige Aktivitätenchronik dieser Person")
        header_lbl.setObjectName("SectionTitle")
        layout.addWidget(header_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._activity_container = QWidget()
        self._activity_layout = QVBoxLayout(self._activity_container)
        self._activity_layout.setContentsMargins(0, 0, 8, 0)
        self._activity_layout.setSpacing(8)
        self._activity_layout.addStretch()
        scroll.setWidget(self._activity_container)
        layout.addWidget(scroll)
        return w

    # ── Tab 5: Personen-Notizen ───────────────────────────────────────────────
    def _build_notes_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header_lbl = QLabel("Interne Notizen zur Person")
        header_lbl.setObjectName("SectionTitle")
        layout.addWidget(header_lbl)

        self.person_note_input = QTextEdit()
        self.person_note_input.setPlaceholderText("Neue interne Notiz eingeben …")
        self.person_note_input.setFixedHeight(80)

        add_note_btn = QPushButton("Notiz hinzufügen")
        add_note_btn.setObjectName("PrimaryButton")
        add_note_btn.clicked.connect(self._add_person_note)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(add_note_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._notes_container = QWidget()
        self._notes_layout = QVBoxLayout(self._notes_container)
        self._notes_layout.setContentsMargins(0, 0, 8, 0)
        self._notes_layout.setSpacing(8)
        self._notes_layout.addStretch()
        scroll.setWidget(self._notes_container)

        layout.addWidget(self.person_note_input)
        layout.addLayout(btn_row)
        layout.addWidget(scroll)
        return w

    # ─────────────────────────────────────────────────────────────────────────
    # Daten laden
    # ─────────────────────────────────────────────────────────────────────────
    def load_person(self) -> None:
        person = self.person_repository.get_person_by_id(self.person_id)
        if not person:
            QMessageBox.critical(self, "Fehler", "Person nicht gefunden.")
            self.reject()
            return
        self._person = dict(person)
        self._fill_person_labels()

    def _fill_person_labels(self) -> None:
        p = self._person
        self.name_label.setText(f"{p.get('first_name', '-')} {p.get('last_name', '-')}")
        self.address_label.setText(p.get("address") or "-")
        self.city_label.setText(
            f"{p.get('postal_code', '')} {p.get('city', '')}".strip() or "-"
        )
        self.email_label.setText(p.get("email") or "-")
        self.birthdate_label.setText(p.get("birthdate") or "-")
        self.category_label.setText(p.get("category_name") or "-")
        self.location_label.setText(p.get("location_name") or "-")
        self.subtitle_lbl.setText(
            f"{p.get('first_name', '')} {p.get('last_name', '')} — Personendossier"
        )
        self.setWindowTitle(f"Dossier: {p.get('first_name', '')} {p.get('last_name', '')}")

    def load_claims(self) -> None:
        self._all_claims = self.claim_service.list_claims(person_id=self.person_id)
        self._render_claims_table(self._all_claims)

    def _render_claims_table(self, claims: list[dict]) -> None:
        self.claims_table.setRowCount(0)
        for claim in claims:
            row = self.claims_table.rowCount()
            self.claims_table.insertRow(row)
            self.claims_table.setItem(row, 0, QTableWidgetItem(claim.get("case_number") or "-"))
            self.claims_table.setItem(row, 1, QTableWidgetItem(ClaimStatus.get_display(claim.get("status") or "") or "-"))
            self.claims_table.setItem(row, 2, QTableWidgetItem(claim.get("category_name") or "-"))
            self.claims_table.setItem(row, 3, QTableWidgetItem(claim.get("location_name") or "-"))
            self.claims_table.setItem(row, 4, QTableWidgetItem((claim.get("created_at") or "")[:10]))
            self.claims_table.setItem(row, 5, QTableWidgetItem(claim.get("review_date") or "-"))
            self.claims_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, claim.get("id"))
            self.claims_table.setRowHeight(row, 44)

    def _filter_claims_table(self, text: str) -> None:
        if not text.strip():
            self._render_claims_table(self._all_claims)
            return
        q = text.strip().lower()
        filtered = [
            c for c in self._all_claims
            if q in (c.get("case_number") or "").lower()
            or q in ClaimStatus.get_display(c.get("status") or "").lower()
            or q in (c.get("category_name") or "").lower()
        ]
        self._render_claims_table(filtered)

    def _open_claim_from_table(self, row: int, _col: int) -> None:
        item = self.claims_table.item(row, 0)
        if not item:
            return
        claim_id = item.data(Qt.ItemDataRole.UserRole)
        if claim_id:
            from ui.pages.claim_detail_page import ClaimDetailPage
            dialog = ClaimDetailPage(claim_id=claim_id, claim_service=self.claim_service)
            dialog.exec()
            self.load_claims()
            self.load_activity_feed()

    def refresh_documents(self) -> None:
        documents = self.document_service.list_documents(person_id=self.person_id)
        self.documents_table.setRowCount(0)
        for row_index, doc in enumerate(documents):
            self.documents_table.insertRow(row_index)
            self.documents_table.setItem(row_index, 0, QTableWidgetItem(doc.get("title", "-")))
            self.documents_table.setItem(row_index, 1, QTableWidgetItem(doc.get("document_type_name", "-")))
            self.documents_table.setItem(row_index, 2, QTableWidgetItem(doc.get("claim_case_number", "-")))
            self.documents_table.setItem(row_index, 3, QTableWidgetItem(doc.get("uploaded_at", "-")))
            self.documents_table.setItem(row_index, 4, QTableWidgetItem(DocumentStatus.get_display(doc.get("status") or "") or "-"))
            open_btn   = QPushButton("Öffnen")
            delete_btn = QPushButton("Löschen")
            open_btn.clicked.connect(lambda _, d=doc["id"]: self.open_document(d))
            delete_btn.clicked.connect(lambda _, d=doc["id"]: self.delete_document(d))
            self.documents_table.setCellWidget(row_index, 5, open_btn)
            self.documents_table.setCellWidget(row_index, 6, delete_btn)

    # ── Aktivitätenchronik ────────────────────────────────────────────────────
    def load_activity_feed(self) -> None:
        events: list[dict] = []

        for claim in self._all_claims:
            cid = claim.get("id")
            if not cid:
                continue
            try:
                history = self.claim_service.get_claim_history(cid)
                for h in history:
                    events.append({
                        "ts":   h.get("changed_at", "")[:19],
                        "type": "status",
                        "text": f"[{claim.get('case_number', '?')}] Status: {ClaimStatus.get_display(h.get('old_status','?'))} → {ClaimStatus.get_display(h.get('new_status','?'))}",
                        "sub":  h.get("note") or "",
                        "color": "#2383e2",
                    })
            except Exception:
                pass

            try:
                feed = self.claim_service.get_activity_feed(cid)
                for entry in feed:
                    if entry.get("kind") == "note":
                        events.append({
                            "ts":    entry.get("created_at", "")[:19],
                            "type":  "note",
                            "text":  f"[{claim.get('case_number', '?')}] Notiz: {entry.get('note_text', '')}",
                            "sub":   f"von {entry.get('user_name', '?')}",
                            "color": "#0f9d58",
                        })
            except Exception:
                pass

        try:
            docs = self.document_service.list_documents(person_id=self.person_id)
            for doc in docs:
                events.append({
                    "ts":    (doc.get("uploaded_at") or "")[:19],
                    "type":  "document",
                    "text":  f"Dokument hochgeladen: {doc.get('title', '-')}",
                    "sub":   doc.get("document_type_name", ""),
                    "color": "#8e44ad",
                })
        except Exception:
            pass

        events.sort(key=lambda e: e.get("ts", ""), reverse=True)

        # Alte Einträge entfernen
        while self._activity_layout.count() > 1:
            item = self._activity_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        if not events:
            empty = QLabel("Noch keine Aktivitäten vorhanden.")
            empty.setStyleSheet("color: #9b9896; font-size: 13px; padding: 16px;")
            self._activity_layout.insertWidget(0, empty)
            return

        for ev in events:
            self._activity_layout.insertWidget(
                self._activity_layout.count() - 1,
                self._make_activity_item(ev),
            )

    def _make_activity_item(self, ev: dict) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #ebebea; border-radius: 10px; }"
        )
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row = QHBoxLayout(frame)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(12)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {ev.get('color', '#2383e2')}; font-size: 16px;")
        dot.setFixedWidth(18)

        info = QVBoxLayout()
        info.setSpacing(2)
        main_lbl = QLabel(ev.get("text", ""))
        main_lbl.setWordWrap(True)
        main_lbl.setStyleSheet("font-size: 13px; font-weight: 500; color: #1a1917;")
        info.addWidget(main_lbl)
        if ev.get("sub"):
            sub_lbl = QLabel(ev["sub"])
            sub_lbl.setStyleSheet("font-size: 11.5px; color: #9b9896;")
            sub_lbl.setWordWrap(True)
            info.addWidget(sub_lbl)

        ts_lbl = QLabel(ev.get("ts", "")[:16])
        ts_lbl.setStyleSheet("font-size: 11px; color: #c0bebb; white-space: nowrap;")
        ts_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        row.addWidget(dot)
        row.addLayout(info, 1)
        row.addWidget(ts_lbl)
        return frame

    # ── Personen-Notizen ──────────────────────────────────────────────────────
    def _load_person_notes(self) -> None:
        try:
            notes = self.person_note_service.list_notes(self.person_id)
        except Exception:
            notes = []
        # Clear existing
        while self._notes_layout.count() > 1:
            item = self._notes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for note in reversed(notes):
            ts     = (note.get("created_at") or "")[:16]
            author = note.get("author_name") or "System"
            frame  = self._make_note_frame(note.get("note_text", ""), ts, author)
            self._notes_layout.insertWidget(0, frame)

    def _add_person_note(self) -> None:
        text = self.person_note_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Eingabe fehlt", "Bitte eine Notiz eingeben.")
            return
        try:
            self.person_note_service.add_note(self.person_id, text)
        except Exception as exc:
            QMessageBox.warning(self, "Fehler", str(exc))
            return
        self.person_note_input.clear()
        self._load_person_notes()

    def _make_note_frame(self, text: str, ts: str, author: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #fdfcf8; border: 1px solid #ebebea; border-radius: 10px; }"
        )
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        header = QHBoxLayout()
        author_lbl = QLabel(author)
        author_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #1a1917;")
        ts_lbl = QLabel(ts[:16])
        ts_lbl.setStyleSheet("font-size: 11px; color: #c0bebb;")
        header.addWidget(author_lbl)
        header.addStretch()
        header.addWidget(ts_lbl)
        text_lbl = QLabel(text)
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet("font-size: 13px; color: #1a1917;")
        layout.addLayout(header)
        layout.addWidget(text_lbl)
        return frame

    # ── Person bearbeiten ─────────────────────────────────────────────────────
    def on_edit_person(self) -> None:
        dlg = _PersonEditDialog(self._person, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                self.person_repository.update_person(self.person_id, data)
                self.load_person()
                QMessageBox.information(self, "Gespeichert", "Personendaten wurden aktualisiert.")
            except Exception as exc:
                QMessageBox.warning(self, "Fehler", str(exc))

    # ── Datei-Upload ──────────────────────────────────────────────────────────
    def on_select_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Dokumente auswählen", str(Path.home()),
            "PDF-Dateien (*.pdf);;Bilder (*.png *.jpg *.jpeg);;Alle Dateien (*)",
        )
        if files:
            self.selected_files = files
            self.file_list_widget.clear()
            for fp in files:
                self.file_list_widget.addItem(fp)

    def on_clear_files(self) -> None:
        self.selected_files = []
        self.file_list_widget.clear()

    def on_upload_files(self) -> None:
        if not self.selected_files:
            QMessageBox.warning(self, "Keine Dateien", "Bitte wählen Sie mindestens eine Datei.")
            return
        doc_type_id = self.document_type_combo.currentData()
        if doc_type_id is None:
            QMessageBox.warning(self, "Typ fehlt", "Bitte wählen Sie einen Dokumenttyp.")
            return
        description = self.document_description_input.text().strip() or None
        errors: list[str] = []
        for fp in self.selected_files:
            try:
                self.document_service.create_document(
                    source_file_path=fp,
                    title=Path(fp).stem,
                    document_type_id=doc_type_id,
                    description=description,
                    person_id=self.person_id,
                )
            except Exception as exc:
                errors.append(f"{Path(fp).name}: {exc}")
        self.on_clear_files()
        self.refresh_documents()
        self.load_activity_feed()
        if errors:
            QMessageBox.warning(self, "Fehler bei Upload", "\n".join(errors))
        else:
            QMessageBox.information(self, "Hochgeladen", "Dokumente wurden hochgeladen.")

    def open_document(self, document_id: int) -> None:
        try:
            path = self.document_service.get_document_path(document_id)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as exc:
            QMessageBox.warning(self, "Fehler", str(exc))

    def delete_document(self, document_id: int) -> None:
        if QMessageBox.question(self, "Löschen", "Dokument wirklich löschen?") != QMessageBox.StandardButton.Yes:
            return
        if self.document_service.delete_document(document_id):
            self.refresh_documents()
            self.load_activity_feed()
        else:
            QMessageBox.warning(self, "Fehler", "Löschen fehlgeschlagen.")

    def on_print_dossier(self) -> None:
        try:
            pdf_path = self.pdf_service.generate_person_dossier_pdf(self.person_id)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf_path)))
            QMessageBox.information(self, "Dossier gedruckt", f"Gespeichert:\n{pdf_path}")
        except Exception as exc:
            QMessageBox.warning(self, "Fehler", str(exc))


# ─── Inline-Edit-Dialog für Personendaten ─────────────────────────────────────
class _PersonEditDialog(QDialog):
    def __init__(self, person: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Person bearbeiten")
        self.setMinimumWidth(460)
        self._person = person
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        form = QFormLayout()
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(20)

        self.first_name = QLineEdit(self._person.get("first_name") or "")
        self.last_name  = QLineEdit(self._person.get("last_name") or "")
        self.address    = QLineEdit(self._person.get("address") or "")
        self.postal     = QLineEdit(self._person.get("postal_code") or "")
        self.city       = QLineEdit(self._person.get("city") or "")
        self.email      = QLineEdit(self._person.get("email") or "")

        form.addRow("Vorname:",    self.first_name)
        form.addRow("Nachname:",   self.last_name)
        form.addRow("Adresse:",    self.address)
        form.addRow("PLZ:",        self.postal)
        form.addRow("Ort:",        self.city)
        form.addRow("E-Mail:",     self.email)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn   = QPushButton("Speichern")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _save(self):
        if not self.first_name.text().strip() or not self.last_name.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Vor- und Nachname sind erforderlich.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "first_name":  self.first_name.text().strip(),
            "last_name":   self.last_name.text().strip(),
            "address":     self.address.text().strip(),
            "postal_code": self.postal.text().strip(),
            "city":        self.city.text().strip(),
            "email":       self.email.text().strip() or None,
        }
