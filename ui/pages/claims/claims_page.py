import csv
import io

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidgetItem, QHeaderView, QScrollArea, QMessageBox,
    QDialog, QVBoxLayout as _VBox, QListWidget, QListWidgetItem,
    QDialogButtonBox, QComboBox, QFileDialog, QInputDialog,
)
from ui.components.table_widget import TableWidget

from core.claim_status import ClaimStatus
from services.card_service import CardService
from services.case_service import CaseService
from services.claim_service import ClaimService
from services.filter_preset_service import FilterPresetService
from ui.components.page_header import PageHeader
from ui.components.action_button import ActionButton
from ui.pages.case_create_page import CaseCreateDialog
from ui.pages.claim_detail_page import ClaimDetailPage


class ClaimsPage(QWidget):
    # Columns available for export
    EXPORT_COLUMNS = [
        ("case_number", "Antragsnummer"),
        ("person_display_name", "Person"),
        ("status", "Status"),
        ("location_name", "Standort"),
        ("examiner_name", "Bearbeiter"),
        ("created_at", "Datum"),
        ("category_name", "Kategorie"),
        ("description", "Beschreibung"),
    ]

    def __init__(
        self,
        claim_service: ClaimService | None = None,
        case_service: CaseService | None = None,
        card_service: CardService | None = None,
        filter_preset_service: FilterPresetService | None = None,
    ):
        super().__init__()
        self.claim_service = claim_service or ClaimService()
        self.case_service = case_service or CaseService()
        self.card_service = card_service or CardService()
        self.filter_preset_service = filter_preset_service or FilterPresetService()
        self.active_filters = {}  # KPI-Filter speichern
        self._current_claims: list[dict] = []
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("claimsPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = PageHeader(
            title="Anträge",
            subtitle="Verwalten Sie Ihre Fälle und eröffnen Sie neue Anträge direkt aus der modernen Oberfläche.",
            action_text="Neuen Antrag anlegen",
            action_callback=self.open_create_dialog,
        )
        layout.addWidget(header)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Suchen nach Nummer, Name oder Status")
        self.search_input.setMinimumWidth(320)
        self.search_input.returnPressed.connect(self.load_claims)
        self.filter_button = ActionButton("Aktualisieren")
        self.filter_button.clicked.connect(self.load_claims)
        filter_row.addWidget(self.search_input)
        filter_row.addWidget(self.filter_button)

        # Filter-Preset-Leiste
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(200)
        self.preset_combo.setPlaceholderText("Filtervorlagen…")
        self._reload_presets()
        load_preset_btn = QPushButton("Laden")
        load_preset_btn.clicked.connect(self._load_selected_preset)
        save_preset_btn = QPushButton("Als Vorlage speichern")
        save_preset_btn.clicked.connect(self._save_current_as_preset)
        del_preset_btn = QPushButton("Vorlage löschen")
        del_preset_btn.clicked.connect(self._delete_selected_preset)
        export_btn = QPushButton("CSV exportieren")
        export_btn.clicked.connect(self._export_csv)
        preset_row.addWidget(self.preset_combo)
        preset_row.addWidget(load_preset_btn)
        preset_row.addWidget(save_preset_btn)
        preset_row.addWidget(del_preset_btn)
        preset_row.addStretch()
        preset_row.addWidget(export_btn)

        layout.addLayout(filter_row)
        layout.addLayout(preset_row)

        self.table = TableWidget(6)
        self.table.setHorizontalHeaderLabels(["Antragsnummer", "Person", "Status", "Standort", "Bearbeiter", "Datum"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.setObjectName("dataTable")
        self.table.cellDoubleClicked.connect(self.on_claim_row_activated)

        content_box = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.table)
        content_box.setLayout(content_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content_box)
        layout.addWidget(scroll)

        self.setLayout(layout)
        self.load_claims()

    def load_claims(self) -> None:
        search_text = self.search_input.text().strip() or None
        status_filter = self.active_filters.get("status")
        statuses_filter = self.active_filters.get("statuses")
        claims = self.claim_service.list_claims(
            search_text=search_text,
            status=status_filter,
            statuses=statuses_filter,
        )
        self._current_claims = claims

        self.table.setRowCount(0)
        if not claims:
            self.table.insertRow(0)
            self.table.setItem(0, 0, QTableWidgetItem("Keine Anträge gefunden."))
            self.table.setSpan(0, 0, 1, self.table.columnCount())
            return

        for claim in claims:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(claim.get("case_number", "-")))
            self.table.setItem(row, 1, QTableWidgetItem(claim.get("person_display_name", "-")))
            self.table.setItem(row, 2, QTableWidgetItem(ClaimStatus.get_display(claim.get("status", "-"))))
            self.table.setItem(row, 3, QTableWidgetItem(claim.get("location_name", "-")))
            self.table.setItem(row, 4, QTableWidgetItem(claim.get("examiner_name", "-")))
            self.table.setItem(row, 5, QTableWidgetItem(claim.get("created_at", "-")))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, claim.get("id"))

    def open_create_dialog(self) -> None:
        dialog = CaseCreateDialog(
            self,
            case_service=self.case_service,
            claim_service=self.claim_service,
        )
        dialog.exec()
        self.load_claims()

    def set_filters(self, filters: dict | None = None) -> None:
        if filters:
            self.active_filters = filters
        self.load_claims()

    def apply_filters(self, status: str | None = None, statuses: list | None = None, **kwargs) -> None:
        self.active_filters = {"status": status, "statuses": statuses}
        self.load_claims()

    # ── Filter-Presets ──────────────────────────────────────────────────────
    def _reload_presets(self) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        try:
            presets = self.filter_preset_service.get_presets()
            for p in presets:
                self.preset_combo.addItem(p["name"], p)
        except Exception:
            pass
        self.preset_combo.blockSignals(False)

    def _load_selected_preset(self) -> None:
        preset = self.preset_combo.currentData()
        if not preset:
            return
        f = preset.get("filter", {})
        self.search_input.setText(f.get("search_text", ""))
        self.active_filters = {k: v for k, v in f.items() if k != "search_text"}
        self.load_claims()

    def _save_current_as_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Vorlage speichern", "Name der Filtervorlage:")
        if not ok or not name.strip():
            return
        filter_dict = {
            "search_text": self.search_input.text().strip(),
            **{k: v for k, v in self.active_filters.items() if v is not None},
        }
        self.filter_preset_service.save_preset(name.strip(), filter_dict)
        self._reload_presets()
        QMessageBox.information(self, "Gespeichert", f"Vorlage «{name.strip()}» wurde gespeichert.")

    def _delete_selected_preset(self) -> None:
        preset = self.preset_combo.currentData()
        if not preset:
            return
        self.filter_preset_service.delete_preset(preset["id"])
        self._reload_presets()

    # ── CSV-Export ──────────────────────────────────────────────────────────
    def _export_csv(self) -> None:
        if not self._current_claims:
            QMessageBox.information(self, "Export", "Keine Daten zum Exportieren.")
            return

        # Column selection dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Spalten auswählen")
        dlg_layout = _VBox(dlg)
        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for key, label in self.EXPORT_COLUMNS:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            list_widget.addItem(item)
            item.setSelected(key in ("case_number", "person_display_name", "status", "location_name"))
        dlg_layout.addWidget(QLabel("Spalten für den Export wählen:"))
        dlg_layout.addWidget(list_widget)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        dlg_layout.addWidget(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        selected_keys = [item.data(Qt.ItemDataRole.UserRole) for item in list_widget.selectedItems()]
        if not selected_keys:
            return

        path, _ = QFileDialog.getSaveFileName(self, "CSV speichern", "antraege.csv", "CSV (*.csv)")
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.DictWriter(fh, fieldnames=selected_keys, extrasaction="ignore")
                header_map = {k: lbl for k, lbl in self.EXPORT_COLUMNS}
                writer.writerow({k: header_map.get(k, k) for k in selected_keys})
                for claim in self._current_claims:
                    row = {k: (ClaimStatus.get_display(claim[k]) if k == "status" else claim.get(k, "")) for k in selected_keys}
                    writer.writerow(row)
            QMessageBox.information(self, "Export abgeschlossen", f"Datei gespeichert:\n{path}")
        except Exception as exc:
            QMessageBox.warning(self, "Fehler beim Export", str(exc))

    def on_claim_row_activated(self, row: int, column: int) -> None:
        item = self.table.item(row, 0)
        if item is None:
            return
        claim_id = item.data(Qt.ItemDataRole.UserRole)
        if not claim_id:
            return

        dialog = ClaimDetailPage(
            claim_id=claim_id,
            claim_service=self.claim_service,
            card_service=self.card_service,
        )
        dialog.exec()
        self.load_claims()
