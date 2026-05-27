"""
M9 – Unterlagen-Checklisten Vorlagen verwalten
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QFormLayout, QLineEdit,
    QCheckBox, QComboBox, QSplitter,
)
from ui.components.page_header import PageHeader
from services.checklist_service import ChecklistService
from services.category_service import CategoryService


class ChecklistTemplatesPage(QWidget):
    def __init__(
        self,
        checklist_service: ChecklistService | None = None,
        category_service: CategoryService | None = None,
    ):
        super().__init__()
        self.svc      = checklist_service or ChecklistService()
        self.cat_svc  = category_service or CategoryService()
        self._templates: list[dict] = []
        self._selected_template: dict | None = None
        self._setup_ui()
        self.refresh_templates()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            title="Unterlagen-Checklisten",
            subtitle="Vorlagen für Unterlagen-Checklisten verwalten und Einträge pflegen.",
        ))

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Linke Seite: Vorlagen-Liste ────────────────────────────────────────
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)

        tpl_hdr = QHBoxLayout()
        tpl_hdr.addWidget(QLabel("<b>Vorlagen</b>"))
        tpl_hdr.addStretch()
        new_tpl_btn = QPushButton("+ Neue Vorlage")
        new_tpl_btn.setObjectName("SoftButton")
        new_tpl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_tpl_btn.clicked.connect(self._new_template)
        tpl_hdr.addWidget(new_tpl_btn)
        left_layout.addLayout(tpl_hdr)

        self._tpl_list = QListWidget()
        self._tpl_list.currentRowChanged.connect(self._on_template_selected)
        left_layout.addWidget(self._tpl_list)

        del_tpl_btn = QPushButton("Vorlage löschen")
        del_tpl_btn.setObjectName("DangerButton")
        del_tpl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_tpl_btn.clicked.connect(self._delete_template)
        left_layout.addWidget(del_tpl_btn)

        splitter.addWidget(left)

        # ── Rechte Seite: Einträge ─────────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)

        items_hdr = QHBoxLayout()
        self._items_title = QLabel("<b>Einträge</b>")
        items_hdr.addWidget(self._items_title, 1)
        add_item_btn = QPushButton("+ Eintrag")
        add_item_btn.setObjectName("SoftButton")
        add_item_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_item_btn.clicked.connect(self._add_item)
        items_hdr.addWidget(add_item_btn)
        right_layout.addLayout(items_hdr)

        self._items_table = QTableWidget()
        self._items_table.setColumnCount(3)
        self._items_table.setHorizontalHeaderLabels(["Bezeichnung", "Pflichtfeld", ""])
        self._items_table.setAlternatingRowColors(True)
        self._items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hh = self._items_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        right_layout.addWidget(self._items_table)

        splitter.addWidget(right)
        splitter.setSizes([250, 550])
        layout.addWidget(splitter)

    def refresh_templates(self):
        self._templates = self.svc.list_templates()
        self._tpl_list.clear()
        for t in self._templates:
            count = t.get("item_count", 0)
            item = QListWidgetItem(f"{t['name']}  ({count})")
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            self._tpl_list.addItem(item)

    def _on_template_selected(self, row: int):
        if row < 0 or row >= len(self._templates):
            self._selected_template = None
            self._items_table.setRowCount(0)
            return
        self._selected_template = self._templates[row]
        self._items_title.setText(f"<b>Einträge: {self._selected_template['name']}</b>")
        self._load_items()

    def _load_items(self):
        if not self._selected_template:
            return
        items = self.svc.list_template_items(self._selected_template["id"])
        self._items_table.setRowCount(len(items))
        for i, item in enumerate(items):
            self._items_table.setItem(i, 0, QTableWidgetItem(item["label"]))
            req = QTableWidgetItem("✓" if item.get("is_required") else "")
            req.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._items_table.setItem(i, 1, req)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(26, 22)
            del_btn.setStyleSheet(
                "QPushButton{background:transparent;color:#c0362a;border:none;font-weight:bold;}"
                "QPushButton:hover{color:#8b0000;}"
            )
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            item_id = item["id"]
            del_btn.clicked.connect(lambda _, iid=item_id: self._delete_item(iid))
            self._items_table.setCellWidget(i, 2, del_btn)

    def _new_template(self):
        categories = []
        try:
            categories = self.cat_svc.list_categories()
        except Exception:
            pass
        dlg = _TemplateDialog(categories=categories, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, cat_id = dlg.get_data()
            try:
                self.svc.create_template(name, cat_id)
                self.refresh_templates()
            except Exception as exc:
                QMessageBox.warning(self, "Fehler", str(exc))

    def _delete_template(self):
        row = self._tpl_list.currentRow()
        if row < 0:
            QMessageBox.information(self, "Hinweis", "Bitte eine Vorlage auswählen.")
            return
        tpl = self._templates[row]
        ans = QMessageBox.question(
            self, "Vorlage löschen",
            f"Vorlage «{tpl['name']}» löschen? Alle Einträge werden entfernt.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.svc.delete_template(tpl["id"])
            self._selected_template = None
            self._items_table.setRowCount(0)
            self.refresh_templates()

    def _add_item(self):
        if not self._selected_template:
            QMessageBox.information(self, "Hinweis", "Bitte zuerst eine Vorlage auswählen.")
            return
        dlg = _ItemDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            label, required = dlg.get_data()
            try:
                self.svc.add_template_item(self._selected_template["id"], label, required)
                self._load_items()
                self.refresh_templates()
            except Exception as exc:
                QMessageBox.warning(self, "Fehler", str(exc))

    def _delete_item(self, item_id: int):
        ans = QMessageBox.question(
            self, "Eintrag löschen", "Eintrag löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.svc.delete_template_item(item_id)
            self._load_items()
            self.refresh_templates()


class _TemplateDialog(QDialog):
    def __init__(self, categories: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neue Vorlage")
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._name = QLineEdit()
        form.addRow("Name *", self._name)
        self._cat_combo = QComboBox()
        self._cat_combo.addItem("(keine Kategorie)", None)
        for c in categories:
            self._cat_combo.addItem(c["name"], c["id"])
        form.addRow("Kategorie", self._cat_combo)
        layout.addLayout(form)

        from PyQt6.QtWidgets import QDialogButtonBox
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_ok(self):
        if not self._name.text().strip():
            QMessageBox.warning(self, "Fehler", "Name ist Pflichtfeld.")
            return
        self.accept()

    def get_data(self) -> tuple[str, int | None]:
        return self._name.text().strip(), self._cat_combo.currentData()


class _ItemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Eintrag hinzufügen")
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._label = QLineEdit()
        form.addRow("Bezeichnung *", self._label)
        self._required_cb = QCheckBox("Pflichtunterlage")
        self._required_cb.setChecked(True)
        form.addRow("", self._required_cb)
        layout.addLayout(form)

        from PyQt6.QtWidgets import QDialogButtonBox
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_ok(self):
        if not self._label.text().strip():
            QMessageBox.warning(self, "Fehler", "Bezeichnung ist Pflichtfeld.")
            return
        self.accept()

    def get_data(self) -> tuple[str, bool]:
        return self._label.text().strip(), self._required_cb.isChecked()
