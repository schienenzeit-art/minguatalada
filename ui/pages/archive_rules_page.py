"""
S7 – Archiv- und Löschregeln
Zeigt alle konfigurierten Aufbewahrungsregeln. Admins können Fristen
und Aktionen anpassen und Regeln manuell ausführen.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QSpinBox, QComboBox, QTextEdit,
    QCheckBox, QFrame,
)
from ui.components.page_header import PageHeader
from services.archive_service import ArchiveService


_ACTION_LABELS = {
    "ARCHIVE": "Archivieren",
    "DELETE":  "Löschen",
}

_ENTITY_LABELS = {
    "claims":     "Anträge",
    "persons":    "Personen",
    "documents":  "Dokumente",
    "cards":      "Karten",
    "audit_logs": "Audit-Protokoll",
}


class ArchiveRulesPage(QWidget):
    def __init__(self, archive_service: ArchiveService | None = None):
        super().__init__()
        self.svc = archive_service or ArchiveService()
        self._rules: list[dict] = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            title="Archiv- und Löschregeln",
            subtitle="Aufbewahrungsfristen und automatische Archivierungsregeln verwalten.",
        ))

        # ── Info-Box ───────────────────────────────────────────────────────────
        info = QFrame()
        info.setObjectName("Card")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(16, 10, 16, 10)
        info_lbl = QLabel(
            "<b>Hinweis:</b> Diese Regeln gelten gemäß DSGVO-Grundsatz der Datensparsamkeit. "
            "Prüfen Sie vor dem Ausführen die Anzahl betroffener Datensätze. "
            "<b>Löschen ist nicht rückgängig zu machen.</b>"
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("font-size: 12px; color: #4a4845;")
        info_layout.addWidget(info_lbl)
        layout.addWidget(info)

        # ── Tabelle ────────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Bereich", "Aufbewahrung (Tage)", "Aktion", "Aktiv", "Zuletzt ausgeführt", "Betroffen"
        ])
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setMinimumHeight(200)
        self._table.doubleClicked.connect(self._edit_selected)
        layout.addWidget(self._table)

        # ── Aktions-Leiste ─────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #9b9896; font-size: 12px;")
        btn_row.addWidget(self._status_lbl, 1)

        edit_btn = QPushButton("Regel bearbeiten")
        edit_btn.setObjectName("SoftButton")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(self._edit_selected)
        btn_row.addWidget(edit_btn)

        run_btn = QPushButton("Regel ausführen")
        run_btn.setObjectName("PrimaryButton")
        run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        run_btn.clicked.connect(self._run_selected)
        btn_row.addWidget(run_btn)

        run_all_btn = QPushButton("Alle aktiven Regeln ausführen")
        run_all_btn.setObjectName("DangerButton")
        run_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        run_all_btn.clicked.connect(self._run_all)
        btn_row.addWidget(run_all_btn)

        layout.addLayout(btn_row)

    def refresh(self):
        self._rules = self.svc.list_rules()
        self._table.setRowCount(len(self._rules))
        for i, rule in enumerate(self._rules):
            entity = _ENTITY_LABELS.get(rule["entity_type"], rule["entity_type"])
            self._table.setItem(i, 0, QTableWidgetItem(entity))
            self._table.setItem(i, 1, QTableWidgetItem(str(rule["retention_days"])))

            action_lbl = _ACTION_LABELS.get(rule["action"], rule["action"])
            action_item = QTableWidgetItem(action_lbl)
            if rule["action"] == "DELETE":
                action_item.setForeground(Qt.GlobalColor.red)
            self._table.setItem(i, 2, action_item)

            active_item = QTableWidgetItem("✓" if rule.get("is_active") else "—")
            active_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 3, active_item)

            last_run = rule.get("last_run_at") or "—"
            self._table.setItem(i, 4, QTableWidgetItem(last_run))

            count = self.svc.count_affected(rule["id"])
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if count > 0 and rule.get("is_active"):
                count_item.setForeground(Qt.GlobalColor.darkRed)
            self._table.setItem(i, 5, count_item)

        self._status_lbl.setText(f"{len(self._rules)} Regeln konfiguriert.")

    def _get_selected_row(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def _edit_selected(self):
        row = self._get_selected_row()
        if row is None:
            QMessageBox.information(self, "Hinweis", "Bitte eine Regel auswählen.")
            return
        rule = self._rules[row]
        dlg = _RuleDialog(rule=rule, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.svc.update_rule(rule["id"], dlg.get_data())
                self.refresh()
            except Exception as exc:
                QMessageBox.warning(self, "Fehler", str(exc))

    def _run_selected(self):
        row = self._get_selected_row()
        if row is None:
            QMessageBox.information(self, "Hinweis", "Bitte eine Regel auswählen.")
            return
        rule = self._rules[row]
        count = self.svc.count_affected(rule["id"])
        entity = _ENTITY_LABELS.get(rule["entity_type"], rule["entity_type"])
        action = _ACTION_LABELS.get(rule["action"], rule["action"])

        ans = QMessageBox.question(
            self,
            "Regel ausführen",
            f"Regel für «{entity}» ausführen?\n"
            f"Aktion: {action} — {count} Datensätze betroffen.\n\n"
            "Diese Aktion kann nicht rückgängig gemacht werden.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            affected = self.svc.run_rule(rule["id"])
            QMessageBox.information(
                self, "Abgeschlossen",
                f"{affected} Datensätze wurden verarbeitet.",
            )
            self.refresh()

    def _run_all(self):
        active = [r for r in self._rules if r.get("is_active")]
        if not active:
            QMessageBox.information(self, "Hinweis", "Keine aktiven Regeln vorhanden.")
            return
        ans = QMessageBox.question(
            self,
            "Alle Regeln ausführen",
            f"Alle {len(active)} aktiven Regeln ausführen?\n\n"
            "Diese Aktion kann nicht rückgängig gemacht werden.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            results = self.svc.run_all_rules()
            summary = "\n".join(
                f"  {_ENTITY_LABELS.get(k, k)}: {v} Datensätze"
                for k, v in results.items()
            )
            QMessageBox.information(self, "Abgeschlossen", f"Ergebnis:\n{summary}")
            self.refresh()


class _RuleDialog(QDialog):
    def __init__(self, rule: dict, parent=None):
        super().__init__(parent)
        self._rule = rule
        entity = _ENTITY_LABELS.get(rule["entity_type"], rule["entity_type"])
        self.setWindowTitle(f"Regel bearbeiten: {entity}")
        self.setMinimumWidth(400)
        self._setup_ui()
        self._fill(rule)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        form = QFormLayout()
        form.setSpacing(8)

        self._retention = QSpinBox()
        self._retention.setRange(1, 36500)
        self._retention.setSuffix(" Tage")
        self._retention.setSingleStep(365)
        form.addRow("Aufbewahrungsdauer", self._retention)

        self._action_combo = QComboBox()
        self._action_combo.addItem("Archivieren", "ARCHIVE")
        self._action_combo.addItem("Löschen", "DELETE")
        form.addRow("Aktion", self._action_combo)

        self._description = QTextEdit()
        self._description.setMaximumHeight(60)
        form.addRow("Beschreibung", self._description)

        self._active_cb = QCheckBox("Regel aktiv")
        form.addRow("", self._active_cb)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.setObjectName("SoftButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("Speichern")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _fill(self, rule: dict):
        self._retention.setValue(rule.get("retention_days", 3650))
        idx = self._action_combo.findData(rule.get("action", "ARCHIVE"))
        if idx >= 0:
            self._action_combo.setCurrentIndex(idx)
        self._description.setPlainText(rule.get("description") or "")
        self._active_cb.setChecked(bool(rule.get("is_active", 1)))

    def get_data(self) -> dict:
        return {
            "retention_days": self._retention.value(),
            "action":         self._action_combo.currentData(),
            "description":    self._description.toPlainText().strip(),
            "is_active":      self._active_cb.isChecked(),
        }
