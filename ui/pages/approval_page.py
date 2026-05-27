"""
M8 – Freigabe-Workflow
Liste aller offenen Freigabeanfragen. Berechtigte können genehmigen
oder ablehnen (mit Begründung).
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QTextEdit, QDialogButtonBox,
)
from ui.components.page_header import PageHeader
from services.approval_service import ApprovalService


_STATUS_COLORS = {
    "PENDING":  ("#fff8e1", "#b8860b"),
    "APPROVED": ("#e8f8ed", "#1a8f4a"),
    "REJECTED": ("#fdeaea", "#c0362a"),
}


def _status_chip(status: str) -> QLabel:
    lbl = QLabel({"PENDING": "Ausstehend", "APPROVED": "Genehmigt", "REJECTED": "Abgelehnt"}.get(status, status))
    bg, fg = _STATUS_COLORS.get(status, ("#f5f5f5", "#333"))
    lbl.setStyleSheet(f"background:{bg}; color:{fg}; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


class ApprovalPage(QWidget):
    def __init__(self, approval_service: ApprovalService | None = None):
        super().__init__()
        self.svc = approval_service or ApprovalService()
        self._requests: list[dict] = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            title="Freigabe-Workflow",
            subtitle="Offene Freigabeanfragen prüfen, genehmigen oder ablehnen.",
        ))

        # ── Tabelle ────────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Aktenzeichen", "Person", "Angefordert von", "Angefordert am", "Status", ""
        ])
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setMinimumHeight(280)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #9b9896; font-size: 12px;")
        btn_row.addWidget(self._status_lbl, 1)

        refresh_btn = QPushButton("Aktualisieren")
        refresh_btn.setObjectName("SoftButton")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(refresh_btn)

        approve_btn = QPushButton("Genehmigen")
        approve_btn.setObjectName("PrimaryButton")
        approve_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        approve_btn.clicked.connect(self._approve_selected)
        btn_row.addWidget(approve_btn)

        reject_btn = QPushButton("Ablehnen")
        reject_btn.setObjectName("DangerButton")
        reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reject_btn.clicked.connect(self._reject_selected)
        btn_row.addWidget(reject_btn)

        layout.addLayout(btn_row)

    def refresh(self):
        self._requests = self.svc.list_pending()
        self._table.setRowCount(len(self._requests))
        for i, req in enumerate(self._requests):
            self._table.setItem(i, 0, QTableWidgetItem(req.get("case_number", "")))
            self._table.setItem(i, 1, QTableWidgetItem(req.get("person_name") or "—"))
            self._table.setItem(i, 2, QTableWidgetItem(req.get("requester_name") or "—"))
            ts = (req.get("requested_at") or "")[:16].replace("T", " ")
            self._table.setItem(i, 3, QTableWidgetItem(ts))
            self._table.setCellWidget(i, 4, _status_chip(req.get("status", "")))
            self._table.setItem(i, 5, QTableWidgetItem(""))

        self._status_lbl.setText(f"{len(self._requests)} offene Anfrage(n).")

    def _get_selected_row(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def _approve_selected(self):
        row = self._get_selected_row()
        if row is None:
            QMessageBox.information(self, "Hinweis", "Bitte eine Anfrage auswählen.")
            return
        req = self._requests[row]
        ans = QMessageBox.question(
            self, "Genehmigen",
            f"Antrag «{req.get('case_number', '')}» genehmigen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            try:
                self.svc.approve(req["id"])
                self.refresh()
            except Exception as exc:
                QMessageBox.warning(self, "Fehler", str(exc))

    def _reject_selected(self):
        row = self._get_selected_row()
        if row is None:
            QMessageBox.information(self, "Hinweis", "Bitte eine Anfrage auswählen.")
            return
        req = self._requests[row]
        dlg = _RejectDialog(case_number=req.get("case_number", ""), parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.svc.reject(req["id"], dlg.get_comment())
                self.refresh()
            except Exception as exc:
                QMessageBox.warning(self, "Fehler", str(exc))


class _RejectDialog(QDialog):
    def __init__(self, case_number: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Ablehnen: {case_number}")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Ablehnungsgrund (Pflichtfeld):"))
        self._comment = QTextEdit()
        self._comment.setMaximumHeight(100)
        layout.addWidget(self._comment)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_ok(self):
        if not self._comment.toPlainText().strip():
            QMessageBox.warning(self, "Fehler", "Ablehnungsgrund ist Pflichtfeld.")
            return
        self.accept()

    def get_comment(self) -> str:
        return self._comment.toPlainText().strip()
