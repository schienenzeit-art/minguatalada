from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidgetItem, QHeaderView, QMessageBox, QInputDialog,
    QTableWidget,
)
from ui.components.page_header import PageHeader
from services.role_service import RoleService


class RoleManagementPage(QWidget):
    def __init__(self, role_service: RoleService | None = None):
        super().__init__()
        self.role_service = role_service or RoleService()
        self.setup_ui()
        self.load_roles()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            title="Rollenverwaltung",
            subtitle="Rollen anlegen, umbenennen und aktivieren/deaktivieren.",
        ))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.add_button = QPushButton("Neue Rolle")
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.clicked.connect(self.on_add_role)
        btn_row.addWidget(self.add_button)

        self.edit_button = QPushButton("Bearbeiten")
        self.edit_button.setObjectName("SoftButton")
        self.edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_button.clicked.connect(self.on_edit_role)
        btn_row.addWidget(self.edit_button)

        self.toggle_button = QPushButton("Aktiv/Inaktiv")
        self.toggle_button.setObjectName("SoftButton")
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_button.clicked.connect(self.on_toggle_active)
        btn_row.addWidget(self.toggle_button)

        btn_row.addStretch()

        self.refresh_button = QPushButton("Aktualisieren")
        self.refresh_button.setObjectName("SoftButton")
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.clicked.connect(self.load_roles)
        btn_row.addWidget(self.refresh_button)

        layout.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Aktiv"])
        self.table.hideColumn(0)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.doubleClicked.connect(self.on_edit_role)
        layout.addWidget(self.table)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #9b9896; font-size: 12px;")
        layout.addWidget(self._status_lbl)

    def load_roles(self):
        roles = self.role_service.list_roles(include_inactive=True)
        self.table.setRowCount(0)
        for role in roles:
            row = self.table.rowCount()
            self.table.insertRow(row)
            id_item = QTableWidgetItem(str(role["id"]))
            id_item.setData(Qt.ItemDataRole.UserRole, role["id"])
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, QTableWidgetItem(role["name"]))
            active = "✓ Aktiv" if role.get("is_active") else "Inaktiv"
            item = QTableWidgetItem(active)
            item.setForeground(Qt.GlobalColor.darkGreen if role.get("is_active") else Qt.GlobalColor.gray)
            self.table.setItem(row, 2, item)
        self._status_lbl.setText(f"{len(roles)} Rolle(n) gesamt.")

    def on_add_role(self):
        name, ok = QInputDialog.getText(self, "Neue Rolle", "Rollenname:")
        if not ok or not name.strip():
            return
        try:
            self.role_service.create_role(name.strip())
            self.load_roles()
        except Exception as exc:
            QMessageBox.warning(self, "Fehler", str(exc))

    def on_edit_role(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Auswahl fehlt", "Bitte eine Rolle auswählen.")
            return
        id_item = self.table.item(row, 0)
        if id_item is None:
            return
        role_id = int(id_item.data(Qt.ItemDataRole.UserRole))
        current_name = self.table.item(row, 1).text()
        name, ok = QInputDialog.getText(
            self, "Rolle bearbeiten", "Rollenname:", text=current_name
        )
        if not ok or not name.strip():
            return
        try:
            self.role_service.update_role(role_id, name.strip())
            self.load_roles()
        except Exception as exc:
            QMessageBox.warning(self, "Fehler", str(exc))

    def on_toggle_active(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Auswahl fehlt", "Bitte eine Rolle auswählen.")
            return
        id_item = self.table.item(row, 0)
        active_item = self.table.item(row, 2)
        if id_item is None or active_item is None:
            return
        role_id = int(id_item.data(Qt.ItemDataRole.UserRole))
        is_active = "Aktiv" in active_item.text()
        try:
            self.role_service.set_role_active(role_id, not is_active)
            self.load_roles()
        except Exception as exc:
            QMessageBox.warning(self, "Fehler", str(exc))
