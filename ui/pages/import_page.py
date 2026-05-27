"""
S3 – Import-Schnittstelle
Unterstützt CSV- und Excel-Import von Personen.
Pflichtfelder: Vorname, Nachname, Adresse, PLZ, Ort
Optionale Felder: E-Mail, Kategorie, Standort
"""

import csv
import io
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame, QComboBox, QCheckBox, QProgressBar,
    QSizePolicy,
)
from ui.components.page_header import PageHeader
from services.location_service import LocationService
from services.category_service import CategoryService
from database.repositories.person_repository import PersonRepository


EXPECTED_COLS = ["Vorname", "Nachname", "Adresse", "PLZ", "Ort", "E-Mail", "Kategorie", "Standort"]
REQUIRED_COLS = {"Vorname", "Nachname", "Adresse", "PLZ", "Ort"}


class ImportPage(QWidget):
    def __init__(
        self,
        location_service: LocationService | None = None,
        category_service: CategoryService | None = None,
    ):
        super().__init__()
        self.location_service  = location_service  or LocationService()
        self.category_service  = category_service  or CategoryService()
        self.person_repo       = PersonRepository()
        self._rows: list[dict] = []
        self._locations: list[dict] = []
        self._categories: list[dict] = []
        self._setup_ui()
        self._load_lookups()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            title="Daten-Import",
            subtitle="Personen aus CSV- oder Excel-Datei importieren. Vorschau vor dem Speichern.",
        ))

        # ── Datei-Auswahl ─────────────────────────────────────────────────────
        file_row = QHBoxLayout()
        file_row.setSpacing(12)

        self._file_label = QLabel("Keine Datei gewählt")
        self._file_label.setStyleSheet("color: #9b9896; font-size: 12px;")
        file_row.addWidget(self._file_label, 1)

        choose_btn = QPushButton("CSV/Excel öffnen …")
        choose_btn.setObjectName("SoftButton")
        choose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_btn.clicked.connect(self._choose_file)
        file_row.addWidget(choose_btn)

        template_btn = QPushButton("Vorlage herunterladen")
        template_btn.setObjectName("SecondaryButton")
        template_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        template_btn.clicked.connect(self._download_template)
        file_row.addWidget(template_btn)

        layout.addLayout(file_row)

        # ── Info-Box mit Spalten-Erklärung ────────────────────────────────────
        info = QFrame()
        info.setObjectName("Card")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_lbl = QLabel(
            f"<b>Erwartete Spalten:</b> {', '.join(EXPECTED_COLS)}<br>"
            f"<b>Pflichtfelder:</b> {', '.join(sorted(REQUIRED_COLS))}<br>"
            "Erste Zeile muss die Spaltenköpfe enthalten. "
            "Trennzeichen: Komma oder Semikolon (CSV) bzw. erste Tabelle (Excel)."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("font-size: 12px; color: #4a4845;")
        info_layout.addWidget(info_lbl)
        layout.addWidget(info)

        # ── Optionen ──────────────────────────────────────────────────────────
        opt_row = QHBoxLayout()
        opt_row.setSpacing(20)
        self._skip_errors_cb = QCheckBox("Fehlerhafte Zeilen überspringen")
        self._skip_errors_cb.setChecked(True)
        opt_row.addWidget(self._skip_errors_cb)

        self._default_location_combo = QComboBox()
        self._default_location_combo.setMinimumWidth(180)
        opt_row.addWidget(QLabel("Standard-Standort:"))
        opt_row.addWidget(self._default_location_combo)
        opt_row.addStretch()
        layout.addLayout(opt_row)

        # ── Vorschau-Tabelle ──────────────────────────────────────────────────
        self._preview_table = QTableWidget()
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._preview_table.setMinimumHeight(220)
        layout.addWidget(self._preview_table)

        # ── Status + Import-Button ─────────────────────────────────────────────
        self._status_lbl = QLabel("Datei öffnen um Vorschau anzuzeigen.")
        self._status_lbl.setStyleSheet("color: #9b9896; font-size: 12px;")

        self._progress = QProgressBar()
        self._progress.setMaximumHeight(8)
        self._progress.hide()

        self._import_btn = QPushButton("Import starten")
        self._import_btn.setObjectName("PrimaryButton")
        self._import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._import_btn.setEnabled(False)
        self._import_btn.clicked.connect(self._run_import)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._status_lbl, 1)
        btn_row.addWidget(self._import_btn)

        layout.addWidget(self._progress)
        layout.addLayout(btn_row)

    # ── Lookups laden ─────────────────────────────────────────────────────────
    def _load_lookups(self):
        self._locations = self.location_service.list_active_locations()
        self._categories = self.category_service.list_categories() if hasattr(self.category_service, "list_categories") else []

        self._default_location_combo.clear()
        self._default_location_combo.addItem("(kein Standard)", None)
        for loc in self._locations:
            self._default_location_combo.addItem(loc["name"], loc["id"])

    # ── Datei öffnen ──────────────────────────────────────────────────────────
    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Datei öffnen", str(Path.home()),
            "CSV/Excel (*.csv *.xlsx *.xls);;Alle Dateien (*)",
        )
        if not path:
            return
        self._file_label.setText(Path(path).name)
        self._parse_file(path)

    def _parse_file(self, path: str):
        try:
            rows = self._read_file(path)
        except Exception as exc:
            QMessageBox.warning(self, "Fehler beim Lesen", str(exc))
            return

        self._rows = rows
        self._show_preview(rows)
        self._status_lbl.setText(f"{len(rows)} Zeile(n) geladen — Import vorbereitet.")
        self._import_btn.setEnabled(len(rows) > 0)

    def _read_file(self, path: str) -> list[dict]:
        p = Path(path)
        if p.suffix.lower() in (".xlsx", ".xls"):
            return self._read_excel(p)
        return self._read_csv(p)

    def _read_csv(self, path: Path) -> list[dict]:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        # Auto-detect delimiter
        sample = text[:2000]
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        return [dict(r) for r in reader]

    def _read_excel(self, path: Path) -> list[dict]:
        try:
            import openpyxl
        except ImportError:
            raise RuntimeError("openpyxl nicht installiert. Bitte 'pip install openpyxl' ausführen.")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(c).strip() if c is not None else "" for c in rows[0]]
        return [dict(zip(headers, r)) for r in rows[1:]]

    # ── Vorschau anzeigen ─────────────────────────────────────────────────────
    def _show_preview(self, rows: list[dict]):
        if not rows:
            self._preview_table.clear()
            self._preview_table.setRowCount(0)
            self._preview_table.setColumnCount(0)
            return

        all_cols = list(rows[0].keys())
        self._preview_table.setColumnCount(len(all_cols) + 1)
        self._preview_table.setHorizontalHeaderLabels(["Status"] + all_cols)
        self._preview_table.setRowCount(min(len(rows), 50))

        for i, row in enumerate(rows[:50]):
            ok, reason = self._validate_row(row)
            status_item = QTableWidgetItem("✓" if ok else f"✗ {reason}")
            status_item.setForeground(
                Qt.GlobalColor.darkGreen if ok else Qt.GlobalColor.red
            )
            self._preview_table.setItem(i, 0, status_item)
            for j, col in enumerate(all_cols):
                self._preview_table.setItem(i, j + 1, QTableWidgetItem(str(row.get(col) or "")))

        if len(rows) > 50:
            self._status_lbl.setText(f"Vorschau: erste 50 von {len(rows)} Zeilen.")

    def _validate_row(self, row: dict) -> tuple[bool, str]:
        # Versuche flexible Spaltenzuordnung
        mapped = self._map_columns(row)
        for col in REQUIRED_COLS:
            if not mapped.get(col, "").strip():
                return False, f"'{col}' fehlt"
        return True, ""

    # ── Spaltenzuordnung ──────────────────────────────────────────────────────
    _COL_ALIASES = {
        "Vorname":   ["vorname", "first_name", "firstname", "f_name"],
        "Nachname":  ["nachname", "name", "last_name", "lastname", "l_name", "familienname"],
        "Adresse":   ["adresse", "address", "strasse", "strasse_nr"],
        "PLZ":       ["plz", "postal_code", "postleitzahl", "zip"],
        "Ort":       ["ort", "city", "gemeinde", "wohnort"],
        "E-Mail":    ["email", "e-mail", "e_mail", "mail"],
        "Kategorie": ["kategorie", "category", "cat"],
        "Standort":  ["standort", "location", "ort2"],
    }

    def _map_columns(self, row: dict) -> dict:
        result = {}
        lower_map = {k.lower().strip(): v for k, v in row.items()}
        for target, aliases in self._COL_ALIASES.items():
            # Direkte Übereinstimmung
            if target in row:
                result[target] = str(row[target] or "")
                continue
            for alias in aliases:
                if alias in lower_map:
                    result[target] = str(lower_map[alias] or "")
                    break
        return result

    # ── Import ────────────────────────────────────────────────────────────────
    def _run_import(self):
        if not self._rows:
            return

        default_location_id = self._default_location_combo.currentData()
        skip_errors = self._skip_errors_cb.isChecked()

        # Kategorie-Lookup
        cat_map = {c["name"].lower(): c["id"] for c in self._categories}

        # Standort-Lookup
        loc_map = {l["name"].lower(): l["id"] for l in self._locations}

        ok_count = err_count = 0
        errors: list[str] = []

        self._progress.setMaximum(len(self._rows))
        self._progress.setValue(0)
        self._progress.show()

        for i, row in enumerate(self._rows):
            self._progress.setValue(i + 1)
            mapped = self._map_columns(row)
            valid, reason = self._validate_row(row)
            if not valid:
                if skip_errors:
                    err_count += 1
                    errors.append(f"Zeile {i+2}: {reason}")
                    continue
                else:
                    QMessageBox.warning(self, "Fehler", f"Zeile {i+2}: {reason}")
                    self._progress.hide()
                    return

            # Standort auflösen
            loc_name = (mapped.get("Standort") or "").lower()
            location_id = loc_map.get(loc_name) or default_location_id

            # Kategorie auflösen
            cat_name = (mapped.get("Kategorie") or "").lower()
            category_id = cat_map.get(cat_name)

            try:
                self.person_repo.create_person({
                    "first_name":  mapped.get("Vorname", "").strip(),
                    "last_name":   mapped.get("Nachname", "").strip(),
                    "address":     mapped.get("Adresse", "").strip(),
                    "postal_code": mapped.get("PLZ", "").strip(),
                    "city":        mapped.get("Ort", "").strip(),
                    "email":       mapped.get("E-Mail", "").strip() or None,
                    "category_id": category_id,
                    "location_id": location_id,
                })
                ok_count += 1
            except Exception as exc:
                err_count += 1
                errors.append(f"Zeile {i+2}: {exc}")
                if not skip_errors:
                    QMessageBox.warning(self, "Fehler", str(exc))
                    self._progress.hide()
                    return

        self._progress.hide()
        summary = f"{ok_count} Personen importiert."
        if err_count:
            summary += f"\n{err_count} Zeile(n) übersprungen."
        if errors:
            summary += "\n\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                summary += f"\n… und {len(errors) - 10} weitere."
        QMessageBox.information(self, "Import abgeschlossen", summary)
        self._rows = []
        self._preview_table.setRowCount(0)
        self._import_btn.setEnabled(False)
        self._status_lbl.setText("Import abgeschlossen.")

    # ── Vorlage ───────────────────────────────────────────────────────────────
    def _download_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Vorlage speichern", str(Path.home() / "import_vorlage.csv"),
            "CSV (*.csv)",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(EXPECTED_COLS)
            writer.writerow(["Max", "Mustermann", "Musterstraße 1", "6700", "Bludenz", "max@example.com", "Allgemein", "Bludenz"])
        QMessageBox.information(self, "Vorlage gespeichert", f"Vorlage unter:\n{path}")
