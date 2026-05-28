"""
Personal-Verwaltung – Anforderung 7: Sidebar Personal
Unterteilt in: Geschäftsführung / Mitarbeiter / Freiwillige

Zugriffsschutz: Nur Standortleitung / Supervisor / Admin dürfen Personal erfassen.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QComboBox, QMessageBox, QAbstractItemView,
)
from PyQt6.QtCore import Qt

from core.session import Session
from services.user_service import UserService

PERSONAL_MANAGEMENT_ROLES = {"Standortleitung", "Supervisor", "Admin"}
STAFF_CATEGORY = "Freiwillige Mitarbeiter"


class PersonalPage(QWidget):
    """Basisseite für Personal-Verwaltung. mode = 'management' | 'staff' | 'volunteers'"""

    MODE_LABELS = {
        "management": "Geschäftsführung",
        "staff":       "Mitarbeiter",
        "volunteers":  "Freiwillige",
    }

    MODE_ROLES = {
        "management": ["Admin", "Standortleitung", "Supervisor"],
        "staff":      ["Mitarbeiter", "Standortleitung", "Supervisor"],
        "volunteers": ["Mitarbeiter"],  # Freiwillige bekommen Mitarbeiter-Rolle
    }

    def __init__(self, mode: str = "staff", user_service: UserService | None = None):
        super().__init__()
        self.mode = mode
        self.user_service = user_service or UserService()
        self._check_permission()
        self.setup_ui()
        self.load_data()

    def _check_permission(self):
        user = Session.get_user() or {}
        role = user.get("role_name", "")
        if role not in PERSONAL_MANAGEMENT_ROLES:
            raise PermissionError(f"Rolle '{role}' hat keinen Zugriff auf den Personalbereich.")

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = self.MODE_LABELS.get(self.mode, "Personal")
        header = QLabel(title)
        header.setObjectName("pageTitle")
        subtitle = QLabel(f"Verwaltung: {title} — Nur für Standortleitung / Supervisor / Admin")
        subtitle.setObjectName("sectionDescription")
        layout.addWidget(header)
        layout.addWidget(subtitle)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton(f"Neuen {title[:-1] if title.endswith('e') else title} anlegen")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.clicked.connect(self.on_add)
        btn_row.addWidget(self.add_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Benutzername", "Rolle", "Standort", "Aktiv"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_data(self):
        self.table.setRowCount(0)
        target_roles = self.MODE_ROLES.get(self.mode, [])
        try:
            users = self.user_service.get_all_users()
            for user in users:
                if user.get("role_name") in target_roles:
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(user.get("full_name", "")))
                    self.table.setItem(row, 1, QTableWidgetItem(user.get("username", "")))
                    self.table.setItem(row, 2, QTableWidgetItem(user.get("role_name", "")))
                    self.table.setItem(row, 3, QTableWidgetItem(user.get("location_name", "")))
                    self.table.setItem(row, 4, QTableWidgetItem("Ja" if user.get("is_active") else "Nein"))
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Personal konnte nicht geladen werden: {e}")

    def on_add(self):
        from ui.pages.personal.staff_form_dialog import StaffFormDialog
        dlg = StaffFormDialog(mode=self.mode, user_service=self.user_service, parent=self)
        if dlg.exec():
            self.load_data()
