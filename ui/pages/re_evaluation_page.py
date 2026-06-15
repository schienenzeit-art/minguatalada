"""Erneute-Prüfung-Freigabe-Seite (Supervisor-Bereich).

Zeigt alle offenen Freigabeanfragen für erneute Prüfungen.
Supervisor kann genehmigen, ablehnen oder kommentieren.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QVBoxLayout as _VBox, QTextEdit, QDialogButtonBox,
    QTabWidget,
)
from ui.components.page_header import PageHeader
from services.re_evaluation_service import ReEvaluationService
from services.service_factory import make_re_evaluation_service


_STATUS_STYLES = {
    "PENDING":  ("Ausstehend",  "#fff8e1", "#b8860b"),
    "APPROVED": ("Genehmigt",   "#e8f8ed", "#1a8f4a"),
    "REJECTED": ("Abgelehnt",   "#fdeaea", "#c0362a"),
}


def _chip(status: str) -> QLabel:
    text, bg, fg = _STATUS_STYLES.get(status, (status, "#f5f5f5", "#333"))
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"background:{bg}; color:{fg}; border-radius:4px; "
        "padding:2px 8px; font-size:11px; font-weight:600;"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


class ReEvaluationPage(QWidget):
    def __init__(self, re_evaluation_service: ReEvaluationService | None = None):
        super().__init__()
        self.svc = re_evaluation_service or make_re_evaluation_service()
        self._pending: list[dict] = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            title="Freigabe erneute Prüfung",
            subtitle="Anträge auf erneute Prüfung durch Mitarbeiter – Freigabe oder Ablehnung.",
        ))

        tabs = QTabWidget()

        # ── Tab: Offene Anfragen ───────────────────────────────────────────────
        pending_tab = QWidget()
        pending_layout = QVBoxLayout(pending_tab)
        pending_layout.setContentsMargins(0, 12, 0, 0)
        pending_layout.setSpacing(12)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Aktenzeichen", "Person", "Angefordert von",
            "Angefordert am", "Begründung", "Status",
        ])
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setMinimumHeight(240)
        pending_layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #9b9896; font-size: 12px;")
        btn_row.addWidget(self._status_lbl, 1)

        refresh_btn = QPushButton("Aktualisieren")
        refresh_btn.setObjectName("SoftButton")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(refresh_btn)

        approve_btn = QPushButton("Freigeben")
        approve_btn.setObjectName("PrimaryButton")
        approve_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        approve_btn.clicked.connect(self._approve_selected)
        btn_row.addWidget(approve_btn)

        reject_btn = QPushButton("Ablehnen")
        reject_btn.setObjectName("DangerButton")
        reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reject_btn.clicked.connect(self._reject_selected)
        btn_row.addWidget(reject_btn)

        pending_layout.addLayout(btn_row)
        tabs.addTab(pending_tab, "Offene Anfragen")

        # ── Hinweis-Box ───────────────────────────────────────────────────────
        info = QLabel(
            "Jeder Mitarbeiter darf einen neuen Antrag nur einmal eigenständig prüfen.\n"
            "Für eine erneute Prüfung muss hier eine Freigabe erteilt werden.\n"
            "Alle Entscheidungen werden im Audit-Protokoll erfasst."
        )
        info.setStyleSheet(
            "background: #e8f0fe; color: #1a3a6b; border-radius: 6px; "
            "padding: 10px 14px; font-size: 12px;"
        )
        info.setWordWrap(True)

        layout.addWidget(info)
        layout.addWidget(tabs)

    def refresh(self):
        self._pending = self.svc.list_pending()
        self._table.setRowCount(len(self._pending))
        for i, req in enumerate(self._pending):
            self._table.setItem(i, 0, QTableWidgetItem(req.get("case_number", "")))
            self._table.setItem(i, 1, QTableWidgetItem(req.get("person_name") or "—"))
            self._table.setItem(i, 2, QTableWidgetItem(req.get("requester_name") or "—"))
            ts = (req.get("requested_at") or "")[:16].replace("T", " ")
            self._table.setItem(i, 3, QTableWidgetItem(ts))
            self._table.setItem(i, 4, QTableWidgetItem(req.get("request_reason") or "—"))
            self._table.setCellWidget(i, 5, _chip(req.get("status", "PENDING")))
            self._table.item(i, 0).setData(Qt.ItemDataRole.UserRole, req.get("id"))
        self._status_lbl.setText(f"{len(self._pending)} offene Anfrage(n).")

    def _selected_request(self) -> dict | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        return self._pending[rows[0].row()]

    def _approve_selected(self):
        req = self._selected_request()
        if req is None:
            QMessageBox.information(self, "Hinweis", "Bitte eine Anfrage auswählen.")
            return
        case = req.get("case_number", "")
        ans = QMessageBox.question(
            self, "Freigeben",
            f"Freigabe zur erneuten Prüfung für Antrag «{case}» erteilen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        # Optionaler Kommentar
        from PyQt6.QtWidgets import QInputDialog
        comment, _ = QInputDialog.getText(self, "Kommentar", "Optionaler Kommentar:")
        try:
            self.svc.approve(req["id"], comment.strip() or None)
            QMessageBox.information(
                self, "Freigegeben",
                f"Freigabe für Antrag «{case}» wurde erteilt.\n"
                "Der Mitarbeiter kann den Antrag jetzt erneut prüfen.",
            )
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))

    def _reject_selected(self):
        req = self._selected_request()
        if req is None:
            QMessageBox.information(self, "Hinweis", "Bitte eine Anfrage auswählen.")
            return
        dlg = _CommentDialog(
            title=f"Ablehnen: {req.get('case_number','')}",
            label="Ablehnungsgrund (Pflichtfeld):",
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.svc.reject(req["id"], dlg.get_text())
            QMessageBox.information(
                self, "Abgelehnt",
                f"Freigabe für Antrag «{req.get('case_number','')}» wurde abgelehnt.",
            )
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))


class _CommentDialog(QDialog):
    def __init__(self, title: str, label: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        layout = _VBox(self)
        layout.addWidget(QLabel(label))
        self._txt = QTextEdit()
        self._txt.setMaximumHeight(100)
        layout.addWidget(self._txt)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_ok(self):
        if not self._txt.toPlainText().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Begründung eingeben.")
            return
        self.accept()

    def get_text(self) -> str:
        return self._txt.toPlainText().strip()
