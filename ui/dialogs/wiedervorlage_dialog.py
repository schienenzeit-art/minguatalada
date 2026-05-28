"""Dialog zum Setzen einer Wiedervorlage / Erinnerung für einen Fall."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDateEdit,
    QDialogButtonBox, QLabel, QMessageBox, QTextEdit,
)
from PyQt6.QtCore import QDate, Qt


class WiedervorlageDialog(QDialog):
    def __init__(
        self,
        claim_id: int | None = None,
        case_number: str = "",
        wiedervorlage_service=None,
        parent=None,
    ):
        super().__init__(parent)
        self._claim_id = claim_id
        self._case_number = case_number
        self._svc = wiedervorlage_service
        self.setWindowTitle("Wiedervorlage setzen")
        self.setMinimumWidth(380)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        if self._case_number:
            info = QLabel(f"Fall: <b>{self._case_number}</b>")
            info.setStyleSheet("color: #4a4845;")
            layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)

        self._date = QDateEdit()
        self._date.setCalendarPopup(True)
        self._date.setDate(QDate.currentDate().addDays(7))
        self._date.setDisplayFormat("dd.MM.yyyy")
        form.addRow("Wiedervorlage am:", self._date)

        self._note = QTextEdit()
        self._note.setMaximumHeight(80)
        self._note.setPlaceholderText("Optionale Notiz / Erinnerungstext …")
        form.addRow("Notiz:", self._note)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_save(self):
        due = self._date.date().toString("yyyy-MM-dd")
        note = self._note.toPlainText().strip() or None
        try:
            svc = self._svc
            if svc is None:
                from services.wiedervorlage_service import WiedervorlageService
                svc = WiedervorlageService()
            svc.create(due_date=due, note=note, claim_id=self._claim_id)
            QMessageBox.information(
                self, "Wiedervorlage gesetzt",
                f"Wiedervorlage am {self._date.date().toString('dd.MM.yyyy')} gesetzt."
            )
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))
