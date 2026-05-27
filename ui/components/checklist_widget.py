"""
M9 – Unterlagen-Checkliste Widget
Einbettbar in den ClaimDetail-Dialog.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QScrollArea, QFrame, QLineEdit, QMessageBox,
    QComboBox, QDialog, QDialogButtonBox,
)
from services.checklist_service import ChecklistService


class ChecklistWidget(QWidget):
    changed = pyqtSignal()

    def __init__(self, claim_id: int,
                 checklist_service: ChecklistService | None = None,
                 parent=None):
        super().__init__(parent)
        self._claim_id = claim_id
        self.svc = checklist_service or ChecklistService()
        self._items: list[dict] = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Header ────────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        self._progress_lbl = QLabel("0 / 0 erledigt")
        self._progress_lbl.setStyleSheet("font-weight: 600; color: #333;")
        header_row.addWidget(self._progress_lbl, 1)

        add_btn = QPushButton("+ Eintrag")
        add_btn.setObjectName("SoftButton")
        add_btn.setMaximumWidth(100)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_item)
        header_row.addWidget(add_btn)

        template_btn = QPushButton("Vorlage")
        template_btn.setObjectName("SoftButton")
        template_btn.setMaximumWidth(90)
        template_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        template_btn.clicked.connect(self._apply_template)
        header_row.addWidget(template_btn)

        layout.addLayout(header_row)

        # ── Scrollable list ───────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_widget)
        layout.addWidget(scroll)

    def refresh(self):
        self._items = self.svc.list_claim_items(self._claim_id)
        self._render_items()
        checked, total = self.svc.completion_rate(self._claim_id)
        color = "#1a8f4a" if (total > 0 and checked == total) else "#333"
        self._progress_lbl.setText(f"{checked} / {total} erledigt")
        self._progress_lbl.setStyleSheet(f"font-weight: 600; color: {color};")

    def _render_items(self):
        # Remove all but the stretch
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for item in self._items:
            row = _ChecklistItemRow(item, self.svc, parent=self)
            row.deleted.connect(self.refresh)
            row.toggled.connect(self._on_toggled)
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)

    def _on_toggled(self):
        self.refresh()
        self.changed.emit()

    def _add_item(self):
        text, ok = _InputDialog.get_text(self, "Eintrag hinzufügen", "Bezeichnung:")
        if ok and text:
            try:
                self.svc.add_claim_item(self._claim_id, text)
                self.refresh()
                self.changed.emit()
            except Exception as exc:
                QMessageBox.warning(self, "Fehler", str(exc))

    def _apply_template(self):
        templates = self.svc.list_templates()
        if not templates:
            QMessageBox.information(self, "Vorlagen", "Keine Vorlagen vorhanden.")
            return
        dlg = _TemplatePickDialog(templates=templates, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            template_id = dlg.get_selected_id()
            if template_id:
                count = self.svc.apply_template(self._claim_id, template_id)
                self.refresh()
                self.changed.emit()
                QMessageBox.information(self, "Vorlage angewendet", f"{count} Einträge hinzugefügt.")


class _ChecklistItemRow(QFrame):
    deleted = pyqtSignal()
    toggled = pyqtSignal()

    def __init__(self, item: dict, svc: ChecklistService, parent=None):
        super().__init__(parent)
        self._item = item
        self.svc   = svc
        self.setObjectName("checklistRow")
        self.setStyleSheet(
            "#checklistRow { background: #fafafa; border: 1px solid #ececec; border-radius: 6px; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self._cb = QCheckBox(item["label"])
        self._cb.setChecked(bool(item.get("is_checked")))
        if item.get("is_required"):
            self._cb.setText(item["label"] + " *")
        self._cb.stateChanged.connect(self._on_toggle)
        layout.addWidget(self._cb, 1)

        if item.get("checked_by_name"):
            by_lbl = QLabel(f"✓ {item['checked_by_name']}")
            by_lbl.setStyleSheet("color: #1a8f4a; font-size: 11px;")
            layout.addWidget(by_lbl)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(22, 22)
        del_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #c0362a; border: none; font-weight:bold; }"
            "QPushButton:hover { color: #8b0000; }"
        )
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(self._on_delete)
        layout.addWidget(del_btn)

    def _on_toggle(self, state: int):
        checked = state == Qt.CheckState.Checked.value
        try:
            self.svc.set_item_checked(self._item["id"], checked)
            self.toggled.emit()
        except Exception as exc:
            QMessageBox.warning(self, "Fehler", str(exc))

    def _on_delete(self):
        ans = QMessageBox.question(
            self, "Löschen",
            f"Eintrag «{self._item['label']}» löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.svc.delete_claim_item(self._item["id"])
            self.deleted.emit()


class _InputDialog(QDialog):
    def __init__(self, parent, title: str, label: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(label))
        self._input = QLineEdit()
        layout.addWidget(self._input)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    @classmethod
    def get_text(cls, parent, title: str, label: str) -> tuple[str, bool]:
        dlg = cls(parent, title, label)
        ok = dlg.exec() == QDialog.DialogCode.Accepted
        return dlg._input.text().strip(), ok


class _TemplatePickDialog(QDialog):
    def __init__(self, templates: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vorlage auswählen")
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Vorlage:"))
        self._combo = QComboBox()
        for t in templates:
            self._combo.addItem(
                f"{t['name']} ({t.get('item_count', 0)} Einträge)",
                t["id"],
            )
        layout.addWidget(self._combo)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_selected_id(self) -> int | None:
        return self._combo.currentData()
