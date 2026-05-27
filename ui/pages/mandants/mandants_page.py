from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QDialog, QFormLayout,
    QLabel, QLineEdit, QPushButton, QTableWidgetItem,
    QHeaderView, QMessageBox, QCheckBox,
)
from ui.components.page_header import PageHeader
from ui.components.table_widget import TableWidget
from services.mandant_service import MandantService


class MandantsPage(QWidget):
    def __init__(self, mandant_service: MandantService | None = None):
        super().__init__()
        self.svc = mandant_service or MandantService()
        self.mandants: list[dict] = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            title="Mandantenverwaltung",
            subtitle="Verwalten Sie Träger-Organisationen und Mandanten.",
            action_text="Neuer Mandant",
            action_callback=self._new,
        ))

        self.table = TableWidget(5)
        self.table.setHorizontalHeaderLabels(["Name", "Kurzname", "E-Mail", "Telefon", "Aktiv"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table)

    def refresh(self):
        self.mandants = self.svc.list_mandants()
        self.table.setRowCount(len(self.mandants))
        for i, m in enumerate(self.mandants):
            self.table.setItem(i, 0, QTableWidgetItem(m.get("name", "")))
            self.table.setItem(i, 1, QTableWidgetItem(m.get("short_name") or ""))
            self.table.setItem(i, 2, QTableWidgetItem(m.get("contact_email") or ""))
            self.table.setItem(i, 3, QTableWidgetItem(m.get("contact_phone") or ""))
            self.table.setItem(i, 4, QTableWidgetItem("Ja" if m.get("is_active") else "Nein"))

    def _new(self):
        dlg = _MandantDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.svc.create_mandant(**dlg.get_data())
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Fehler", str(e))

    def _edit_selected(self, row: int, _col: int):
        if row >= len(self.mandants):
            return
        m = self.mandants[row]
        dlg = _MandantDialog(mandant=m, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.svc.update_mandant(m["id"], dlg.get_data())
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Fehler", str(e))


class _MandantDialog(QDialog):
    def __init__(self, mandant: dict | None = None, parent=None):
        super().__init__(parent)
        self._mandant = mandant
        self.setWindowTitle("Mandant bearbeiten" if mandant else "Neuer Mandant")
        self.setMinimumWidth(440)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        form = QFormLayout()
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(20)

        m = self._mandant or {}
        self.name        = QLineEdit(m.get("name", ""))
        self.short_name  = QLineEdit(m.get("short_name") or "")
        self.email       = QLineEdit(m.get("contact_email") or "")
        self.phone       = QLineEdit(m.get("contact_phone") or "")
        self.address     = QLineEdit(m.get("address") or "")
        self.active_cb   = QCheckBox("Aktiv")
        self.active_cb.setChecked(bool(m.get("is_active", True)))

        form.addRow("Name *:",        self.name)
        form.addRow("Kurzname:",      self.short_name)
        form.addRow("E-Mail:",        self.email)
        form.addRow("Telefon:",       self.phone)
        form.addRow("Adresse:",       self.address)
        form.addRow("",               self.active_cb)
        layout.addLayout(form)

        row = QHBoxLayout()
        row.addStretch()
        save = QPushButton("Speichern")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._save)
        cancel = QPushButton("Abbrechen")
        cancel.clicked.connect(self.reject)
        row.addWidget(save)
        row.addWidget(cancel)
        layout.addLayout(row)

    def _save(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Name ist erforderlich.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name":          self.name.text().strip(),
            "short_name":    self.short_name.text().strip(),
            "contact_email": self.email.text().strip(),
            "contact_phone": self.phone.text().strip(),
            "address":       self.address.text().strip(),
            "is_active":     self.active_cb.isChecked(),
        }
