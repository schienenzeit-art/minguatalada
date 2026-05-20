from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QScrollArea,
    QTableWidgetItem,
    QTextEdit,
    QMessageBox,
)
from ui.components.table_widget import TableWidget
from PyQt6.QtCore import Qt

from core.session import Session
from services.settings_service import SettingsService
from ui.components.page_header import PageHeader
from ui.components.action_button import ActionButton


class SettingsPage(QWidget):
    def __init__(self, settings_service: SettingsService | None = None):
        super().__init__()
        self.settings_service = settings_service or SettingsService()
        self.is_admin = Session.is_admin()
        self.settings = []
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("settingsPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = PageHeader(
            title="Einstellungen",
            subtitle="Systemweite Prüfparameter und Konfigurationswerte.",
        )
        layout.addWidget(header)

        info_card = QGroupBox("Systeminformationen")
        info_card.setObjectName("pageSection")
        settings_layout = QFormLayout()
        settings_layout.addRow("Version:", QLabel("1.0.0"))
        settings_layout.addRow("Datenbank:", QLabel("SQLite"))
        settings_layout.addRow("Aktueller Benutzer:", QLabel(Session.get_full_name() or "-"))
        settings_layout.addRow("Rolle:", QLabel(Session.get_role_name() or "-"))
        info_card.setLayout(settings_layout)
        layout.addWidget(info_card)

        self.settings_table = TableWidget(5)
        self.settings_table.setColumnCount(5)
        self.settings_table.setHorizontalHeaderLabels(
            ["Schlüssel", "Wert", "Typ", "Kategorie", "Beschreibung"]
        )
        self.settings_table.horizontalHeader().setStretchLastSection(True)
        self.settings_table.setEditTriggers(
            TableWidget.EditTrigger.DoubleClicked
            if self.is_admin
            else TableWidget.EditTrigger.NoEditTriggers
        )
        layout.addWidget(self.settings_table)

        if not self.is_admin:
            warning_label = QLabel(
                "Nur Admin-Benutzer dürfen Prüfparameter ändern. Werte sind hier angezeigt, aber nicht bearbeitbar."
            )
            warning_label.setWordWrap(True)
            layout.addWidget(warning_label)

        comment_card = QGroupBox("Änderungskommentar")
        comment_card.setObjectName("pageSection")
        comment_layout = QVBoxLayout()
        self.comment_input = QTextEdit()
        self.comment_input.setPlaceholderText(
            "Begründung für diese Änderung eingeben (optional)."
        )
        self.comment_input.setFixedHeight(100)
        self.comment_input.setEnabled(self.is_admin)
        comment_layout.addWidget(self.comment_input)
        comment_card.setLayout(comment_layout)
        layout.addWidget(comment_card)

        action_row = QHBoxLayout()
        action_row.addStretch()
        self.save_button = ActionButton("Speichern")
        self.save_button.setEnabled(self.is_admin)
        self.save_button.clicked.connect(self.on_save_clicked)
        action_row.addWidget(self.save_button)
        layout.addLayout(action_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setLayout(layout)
        scroll.setWidget(content)

        outer_layout = QVBoxLayout()
        outer_layout.addWidget(scroll)
        self.setLayout(outer_layout)

        self.load_settings()

    def load_settings(self) -> None:
        self.settings = self.settings_service.get_all_settings()
        self.settings_table.setRowCount(len(self.settings))

        for row, setting in enumerate(self.settings):
            key_item = QTableWidgetItem(setting["key"])
            key_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.settings_table.setItem(row, 0, key_item)

            value_item = QTableWidgetItem(str(setting["value"]))
            if self.is_admin and setting["editable_by_admin"]:
                value_item.setFlags(
                    Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsEditable
                )
            else:
                value_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.settings_table.setItem(row, 1, value_item)

            type_item = QTableWidgetItem(setting["value_type"])
            type_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.settings_table.setItem(row, 2, type_item)

            category_item = QTableWidgetItem(setting.get("category") or "-")
            category_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.settings_table.setItem(row, 3, category_item)

            description_item = QTableWidgetItem(setting.get("description") or "-")
            description_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.settings_table.setItem(row, 4, description_item)

        self.settings_table.resizeColumnsToContents()

    def on_save_clicked(self) -> None:
        updated_keys = []
        comment = self.comment_input.toPlainText().strip() or None

        for row, setting in enumerate(self.settings):
            if not setting["editable_by_admin"]:
                continue

            value_item = self.settings_table.item(row, 1)
            if value_item is None:
                continue

            new_text = value_item.text().strip()
            old_value = setting["value"]
            if new_text == str(old_value):
                continue

            try:
                if setting["value_type"] == "number":
                    new_value = float(new_text)
                elif setting["value_type"] == "boolean":
                    new_value = new_text.lower() in ("1", "true", "yes")
                else:
                    new_value = new_text
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Ungültiger Wert",
                    f"Der Wert für {setting['key']} ist ungültig.",
                )
                return

            try:
                self.settings_service.update_setting(setting["key"], new_value, comment=comment)
                updated_keys.append(setting["key"])
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "Fehler beim Speichern",
                    f"Konnte Einstellung {setting['key']} nicht speichern: {exc}",
                )
                return

        if not updated_keys:
            QMessageBox.information(self, "Keine Änderungen", "Es wurden keine geänderten Werte gefunden.")
            return

        QMessageBox.information(
            self,
            "Erfolg",
            f"Einstellungen aktualisiert: {', '.join(updated_keys)}.",
        )
        self.load_settings()
