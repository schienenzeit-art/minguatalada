"""
S5 – Terminverwaltung
Listenansicht mit Filter, Neu/Bearbeiten/Löschen-Dialog.
"""

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QComboBox, QDialog, QFormLayout, QLineEdit, QTextEdit,
    QDateEdit, QTimeEdit, QSpinBox, QFrame, QSizePolicy,
)
from ui.components.page_header import PageHeader
from services.appointment_service import AppointmentService, APPOINTMENT_STATUSES
from services.location_service import LocationService
from services.user_service import UserService


_STATUS_COLORS = {
    "GEPLANT":       ("#e8f4f8", "#2383e2"),
    "BESTÄTIGT":     ("#e8f8ed", "#1a8f4a"),
    "ABGESCHLOSSEN": ("#f0f0f0", "#666"),
    "ABGESAGT":      ("#fdeaea", "#c0362a"),
}


def _status_label(status: str) -> QLabel:
    lbl = QLabel(status)
    bg, fg = _STATUS_COLORS.get(status, ("#f5f5f5", "#333"))
    lbl.setStyleSheet(
        f"background:{bg}; color:{fg}; border-radius:4px; "
        f"padding:2px 8px; font-size:11px; font-weight:600;"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


class AppointmentsPage(QWidget):
    def __init__(
        self,
        appointment_service: AppointmentService | None = None,
        location_service: LocationService | None = None,
        user_service: UserService | None = None,
    ):
        super().__init__()
        self.apt_service = appointment_service or AppointmentService()
        self.loc_service = location_service or LocationService()
        self.usr_service = user_service or UserService()
        self._appointments: list[dict] = []
        self._locations: list[dict] = []
        self._users: list[dict] = []
        self._setup_ui()
        self._load_lookups()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            title="Termine",
            subtitle="Terminübersicht und -verwaltung. Neu anlegen, bearbeiten oder absagen.",
        ))

        # ── Filter-Leiste ──────────────────────────────────────────────────────
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        self._status_combo = QComboBox()
        self._status_combo.setMinimumWidth(160)
        self._status_combo.addItem("Alle Status", None)
        for s in APPOINTMENT_STATUSES:
            self._status_combo.addItem(s, s)
        self._status_combo.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(QLabel("Status:"))
        filter_row.addWidget(self._status_combo)

        self._from_date = QDateEdit()
        self._from_date.setCalendarPopup(True)
        self._from_date.setDate(QDate.currentDate())
        self._from_date.setSpecialValueText("(kein Filter)")
        self._from_date.setDisplayFormat("dd.MM.yyyy")
        filter_row.addWidget(QLabel("Von:"))
        filter_row.addWidget(self._from_date)

        self._to_date = QDateEdit()
        self._to_date.setCalendarPopup(True)
        self._to_date.setDate(QDate.currentDate().addMonths(3))
        self._to_date.setDisplayFormat("dd.MM.yyyy")
        filter_row.addWidget(QLabel("Bis:"))
        filter_row.addWidget(self._to_date)

        filter_row.addStretch()

        refresh_btn = QPushButton("Aktualisieren")
        refresh_btn.setObjectName("SoftButton")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)
        filter_row.addWidget(refresh_btn)

        new_btn = QPushButton("+ Neuer Termin")
        new_btn.setObjectName("PrimaryButton")
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.clicked.connect(self._new_appointment)
        filter_row.addWidget(new_btn)

        layout.addLayout(filter_row)

        # ── Tabelle ────────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Datum", "Uhrzeit", "Titel", "Person", "Mitarbeiter", "Standort", "Status"
        ])
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setMinimumHeight(300)
        self._table.doubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self._table)

        # ── Status-Zeile ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #9b9896; font-size: 12px;")
        btn_row.addWidget(self._status_lbl, 1)

        edit_btn = QPushButton("Bearbeiten")
        edit_btn.setObjectName("SoftButton")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(self._edit_selected)
        btn_row.addWidget(edit_btn)

        delete_btn = QPushButton("Löschen")
        delete_btn.setObjectName("DangerButton")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(delete_btn)

        layout.addLayout(btn_row)

    def _load_lookups(self):
        self._locations = self.loc_service.list_active_locations()
        try:
            self._users = self.usr_service.get_all_users()
        except Exception:
            self._users = []

    def refresh(self):
        status = self._status_combo.currentData()
        from_d = self._from_date.date().toString("yyyy-MM-dd")
        to_d   = self._to_date.date().toString("yyyy-MM-dd")
        self._appointments = self.apt_service.list_appointments(
            status=status,
            from_date=from_d,
            to_date=to_d,
        )
        self._render_table()

    def _render_table(self):
        apts = self._appointments
        self._table.setRowCount(len(apts))
        for i, a in enumerate(apts):
            date_str = a.get("appointment_date", "")
            # Format date for display
            try:
                from datetime import datetime
                date_str = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
            except Exception:
                pass

            self._table.setItem(i, 0, QTableWidgetItem(date_str))
            self._table.setItem(i, 1, QTableWidgetItem(a.get("appointment_time") or ""))
            self._table.setItem(i, 2, QTableWidgetItem(a.get("title", "")))
            self._table.setItem(i, 3, QTableWidgetItem(a.get("person_name") or "—"))
            self._table.setItem(i, 4, QTableWidgetItem(a.get("user_name") or "—"))
            self._table.setItem(i, 5, QTableWidgetItem(a.get("location_name") or "—"))

            status = a.get("status", "")
            status_lbl = _status_label(status)
            self._table.setCellWidget(i, 6, status_lbl)

        self._status_lbl.setText(f"{len(apts)} Termin(e) gefunden.")

    def _get_selected_row(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        return rows[0].row()

    def _on_row_double_clicked(self, index):
        self._edit_selected()

    def _new_appointment(self):
        dlg = _AppointmentDialog(
            locations=self._locations,
            users=self._users,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.apt_service.create_appointment(dlg.get_data())
                self.refresh()
            except Exception as exc:
                QMessageBox.warning(self, "Fehler", str(exc))

    def _edit_selected(self):
        row = self._get_selected_row()
        if row is None:
            QMessageBox.information(self, "Hinweis", "Bitte einen Termin auswählen.")
            return
        apt = self._appointments[row]
        dlg = _AppointmentDialog(
            locations=self._locations,
            users=self._users,
            appointment=apt,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.apt_service.update_appointment(apt["id"], dlg.get_data())
                self.refresh()
            except Exception as exc:
                QMessageBox.warning(self, "Fehler", str(exc))

    def _delete_selected(self):
        row = self._get_selected_row()
        if row is None:
            QMessageBox.information(self, "Hinweis", "Bitte einen Termin auswählen.")
            return
        apt = self._appointments[row]
        ans = QMessageBox.question(
            self, "Termin löschen",
            f"Termin «{apt['title']}» vom {apt.get('appointment_date','')} wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.apt_service.delete_appointment(apt["id"])
            self.refresh()


class _AppointmentDialog(QDialog):
    def __init__(self, locations: list[dict], users: list[dict],
                 appointment: dict | None = None, parent=None):
        super().__init__(parent)
        self._apt = appointment
        self._locations = locations
        self._users = users
        self.setWindowTitle("Termin bearbeiten" if appointment else "Neuer Termin")
        self.setMinimumWidth(480)
        self._setup_ui()
        if appointment:
            self._fill(appointment)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        form = QFormLayout()
        form.setSpacing(8)

        self._title = QLineEdit()
        self._title.setPlaceholderText("z. B. Erstgespräch, Dokumentenübergabe …")
        form.addRow("Titel *", self._title)

        date_row = QHBoxLayout()
        self._date = QDateEdit()
        self._date.setCalendarPopup(True)
        self._date.setDate(QDate.currentDate())
        self._date.setDisplayFormat("dd.MM.yyyy")
        date_row.addWidget(self._date)
        date_row.addWidget(QLabel("Uhrzeit:"))
        self._time = QLineEdit()
        self._time.setPlaceholderText("HH:MM")
        self._time.setMaximumWidth(80)
        date_row.addWidget(self._time)
        date_row.addWidget(QLabel("Dauer (Min.):"))
        self._duration = QSpinBox()
        self._duration.setRange(5, 480)
        self._duration.setValue(30)
        self._duration.setSingleStep(15)
        date_row.addWidget(self._duration)
        form.addRow("Datum *", date_row)

        self._status_combo = QComboBox()
        for s in APPOINTMENT_STATUSES:
            self._status_combo.addItem(s, s)
        form.addRow("Status", self._status_combo)

        self._location_combo = QComboBox()
        self._location_combo.addItem("(kein Standort)", None)
        for loc in self._locations:
            self._location_combo.addItem(loc["name"], loc["id"])
        form.addRow("Standort", self._location_combo)

        self._user_combo = QComboBox()
        self._user_combo.addItem("(kein Mitarbeiter)", None)
        for u in self._users:
            self._user_combo.addItem(u.get("full_name", u.get("username", "-")), u["id"])
        form.addRow("Mitarbeiter", self._user_combo)

        self._note = QTextEdit()
        self._note.setPlaceholderText("Interne Notiz zum Termin …")
        self._note.setMaximumHeight(80)
        form.addRow("Notiz", self._note)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.setObjectName("SoftButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("Speichern")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _fill(self, apt: dict):
        self._title.setText(apt.get("title", ""))
        date_str = apt.get("appointment_date", "")
        try:
            from datetime import datetime
            qdate = QDate.fromString(date_str, "yyyy-MM-dd")
            self._date.setDate(qdate)
        except Exception:
            pass
        self._time.setText(apt.get("appointment_time") or "")
        self._duration.setValue(apt.get("duration_minutes") or 30)
        # Status
        idx = self._status_combo.findData(apt.get("status"))
        if idx >= 0:
            self._status_combo.setCurrentIndex(idx)
        # Location
        idx = self._location_combo.findData(apt.get("location_id"))
        if idx >= 0:
            self._location_combo.setCurrentIndex(idx)
        # User
        idx = self._user_combo.findData(apt.get("user_id"))
        if idx >= 0:
            self._user_combo.setCurrentIndex(idx)
        self._note.setPlainText(apt.get("note") or "")

    def _on_save(self):
        if not self._title.text().strip():
            QMessageBox.warning(self, "Fehler", "Titel ist Pflichtfeld.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "title":            self._title.text().strip(),
            "appointment_date": self._date.date().toString("yyyy-MM-dd"),
            "appointment_time": self._time.text().strip() or None,
            "duration_minutes": self._duration.value(),
            "status":           self._status_combo.currentData(),
            "location_id":      self._location_combo.currentData(),
            "user_id":          self._user_combo.currentData(),
            "note":             self._note.toPlainText().strip() or None,
        }
