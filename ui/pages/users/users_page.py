from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidgetItem, QHeaderView, QScrollArea, QMessageBox, QDialog,
    QFormLayout, QDateTimeEdit, QDialogButtonBox,
)
from PyQt6.QtCore import QDateTime

from PyQt6.QtGui import QColor

from ui.components.table_widget import TableWidget
from core.constants import NON_LOGIN_ROLES
from services.user_service import UserService, USERMGMT_ALLOWED_ROLES
from ui.components.page_header import PageHeader
from ui.components.action_button import ActionButton
from ui.dialogs.user_dialog import AddUserDialog
from core.session import Session


class UsersPage(QWidget):
    def __init__(self, user_service: UserService | None = None):
        super().__init__()
        self.user_service = user_service or UserService()
        role = (Session.get_user() or {}).get("role_name", "")
        if role not in USERMGMT_ALLOWED_ROLES:
            self._setup_denied_ui()
            return
        self.setup_ui()
        self.load_users()

    def _setup_denied_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 60, 40, 40)
        lbl = QLabel("Zugriff verweigert – Sie haben keine Berechtigung für die Benutzerverwaltung.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #b42318; font-size: 15px; font-weight: 600;")
        layout.addWidget(lbl)
        layout.addStretch()

    def setup_ui(self):
        self.setObjectName("usersPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = PageHeader(
            title="Benutzerverwaltung",
            subtitle="Verwalten Sie Benutzer, Rollen und Zugriffsübersichten.",
            action_text="Benutzer hinzufügen",
            action_callback=self.open_add_user_dialog,
        )
        layout.addWidget(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Benutzername, Rolle oder Standort suchen")
        self.search_input.setMinimumWidth(320)
        self.search_input.returnPressed.connect(self.load_users)
        self.filter_button = ActionButton("Aktualisieren")
        self.filter_button.clicked.connect(self.load_users)
        toolbar.addWidget(self.search_input)
        toolbar.addWidget(self.filter_button)
        layout.addLayout(toolbar)

        self.table = TableWidget(8)
        self.table.setHorizontalHeaderLabels(["Name", "Benutzername", "Rolle", "Typ", "Standort", "Status", "PW ändern", "Gesperrt bis"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.setObjectName("dataTable")
        self.table.cellDoubleClicked.connect(self.on_user_row_double_clicked)

        content_box = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.table)
        content_box.setLayout(content_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content_box)
        layout.addWidget(scroll)

        action_bar = QHBoxLayout()
        action_bar.addStretch()
        self.lock_button = QPushButton("Sperren bis…")
        self.lock_button.setEnabled(False)
        self.lock_button.clicked.connect(self.lock_selected_user)
        self.unlock_button = QPushButton("Entsperren")
        self.unlock_button.setEnabled(False)
        self.unlock_button.clicked.connect(self.unlock_selected_user)
        action_bar.addWidget(self.lock_button)
        action_bar.addWidget(self.unlock_button)
        layout.addLayout(action_bar)

        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)

        # Sperren/Entsperren nicht für Freiwillige
        self.table.selectionModel().selectionChanged.connect(self._update_lock_buttons)
        self.setLayout(layout)

    def _current_user_id(self) -> int | None:
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            return None
        item = self.table.item(selected[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_selection_changed(self) -> None:
        has_sel = bool(self.table.selectionModel().selectedRows())
        self.lock_button.setEnabled(has_sel)
        self.unlock_button.setEnabled(has_sel)

    def _update_lock_buttons(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.lock_button.setEnabled(False)
            self.unlock_button.setEnabled(False)
            return
        # Sperren/Entsperren für Freiwillige deaktivieren
        role_item = self.table.item(rows[0].row(), 2)
        is_volunteer = role_item and role_item.text() in NON_LOGIN_ROLES
        self.lock_button.setEnabled(not is_volunteer)
        self.unlock_button.setEnabled(not is_volunteer)

    def lock_selected_user(self) -> None:
        user_id = self._current_user_id()
        if not user_id:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Benutzer sperren bis…")
        form = QFormLayout(dlg)
        dt_edit = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        dt_edit.setCalendarPopup(True)
        dt_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        form.addRow("Gesperrt bis:", dt_edit)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        iso = dt_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss")
        self.user_service.manual_lock_user(user_id, iso)
        self.load_users()

    def unlock_selected_user(self) -> None:
        user_id = self._current_user_id()
        if not user_id:
            return
        self.user_service.manual_lock_user(user_id, None)
        self.load_users()

    def load_users(self) -> None:
        users = self.user_service.get_all_users()

        self.table.setRowCount(0)
        for user in users:
            display_name = user.get("full_name", "-")
            username = user.get("username", "-")
            role = user.get("role_name", "-")
            is_volunteer = role in NON_LOGIN_ROLES
            user_type = "Freiwillige/r" if is_volunteer else "Systembenutzer"
            location = user.get("location_name", "-") or "-"
            status = "Aktiv" if user.get("is_active") else "Inaktiv"
            pw_flag = "–" if is_volunteer else ("Ja" if user.get("must_change_password") else "Nein")
            locked_until = "–" if is_volunteer else ((user.get("locked_until") or "")[:16].replace("T", " ") or "–")

            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(display_name))
            self.table.setItem(row, 1, QTableWidgetItem(username))
            self.table.setItem(row, 2, QTableWidgetItem(role))
            self.table.setItem(row, 3, QTableWidgetItem(user_type))
            self.table.setItem(row, 4, QTableWidgetItem(location))
            self.table.setItem(row, 5, QTableWidgetItem(status))
            self.table.setItem(row, 6, QTableWidgetItem(pw_flag))
            self.table.setItem(row, 7, QTableWidgetItem(locked_until))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, user.get("id"))

            # Freiwillige optisch hervorheben (gedämpfte Farbe)
            if is_volunteer:
                for col in range(8):
                    item = self.table.item(row, col)
                    if item:
                        item.setForeground(QColor("#888"))
                type_item = self.table.item(row, 3)
                if type_item:
                    type_item.setForeground(QColor("#e67e22"))
                    type_item.setToolTip("Freiwillige erhalten keinen Systemzugang.")

    def open_add_user_dialog(self) -> None:
        roles = self.user_service.get_roles()
        locations = self.user_service.get_locations()
        dialog = AddUserDialog(roles=roles, locations=locations)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        user_data = dialog.get_user_data()
        result = self.user_service.create_user(
            full_name=user_data["full_name"],
            username=user_data["username"],
            password=user_data["password"],
            role_id=user_data["role_id"],
            location_id=user_data["location_id"],
            is_active=user_data["is_active"],
        )

        if not result["success"]:
            QMessageBox.warning(self, "Fehler", result["message"])
            return

        if user_data.get("is_volunteer"):
            QMessageBox.information(
                self, "Freiwillige/r angelegt",
                f"Freiwillige/r «{user_data['full_name']}» wurde erfolgreich angelegt.\n\n"
                f"Benutzername: {user_data['username']}\n\n"
                "Freiwillige erhalten keinen Systemzugang.\n"
                "Der Datensatz dient der Verwaltung und Kartenzuordnung.",
            )
        else:
            QMessageBox.information(
                self, "Benutzer angelegt",
                f"Benutzer «{user_data['full_name']}» wurde erfolgreich angelegt.\n\n"
                f"Benutzername: {user_data['username']}\n"
                f"Initialpasswort: {user_data['password']}\n\n"
                "Das Passwort muss bei der ersten Anmeldung geändert werden.\n"
                "Bitte geben Sie diese Login-Daten persönlich an den Mitarbeiter weiter.",
            )
        self.load_users()

    def on_user_row_double_clicked(self, row: int, _column: int) -> None:
        user_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not user_id:
            return

        user = next((u for u in self.user_service.get_all_users() if u.get("id") == user_id), None)
        if user is None:
            return

        roles = self.user_service.get_roles()
        locations = self.user_service.get_locations()
        dialog = AddUserDialog(roles=roles, locations=locations, user=user)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        user_data = dialog.get_user_data()
        result = self.user_service.update_user(
            user_id=user_id,
            full_name=user_data["full_name"],
            username=user_data["username"],
            role_id=user_data["role_id"],
            location_id=user_data["location_id"],
            is_active=user_data["is_active"],
            password=user_data.get("password"),
        )

        if not result["success"]:
            QMessageBox.warning(self, "Fehler", result["message"])
            return

        QMessageBox.information(self, "Erfolg", result["message"])
        self.load_users()
