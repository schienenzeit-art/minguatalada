from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QSizePolicy, QMessageBox,
    QScrollArea,
)

from core.session import Session
from services.settings_service import SettingsService
from ui.components.page_header import PageHeader


_CATEGORIES = [
    {
        "key":         "settings_pruefung",
        "title":       "Prüfungslimits",
        "description": "Anspruchsgrenzen, Zuschläge und Härtefallmultiplikator für die Anspruchsprüfung.",
        "detail":      "BASE_LIMIT · ADDITIONAL_ADULT_LIMIT · CHILD_LIMIT · HARDSHIP_FACTOR",
        "action":      "navigate",
    },
    {
        "key":         "smtp_settings",
        "title":       "SMTP & E-Mail",
        "description": "Mailserver, Absenderadresse, STARTTLS und Verbindungstest.",
        "detail":      "SMTP_HOST · SMTP_PORT · SMTP_USER · SMTP_FROM_EMAIL",
        "action":      "navigate",
    },
    {
        "key":         "software_update",
        "title":       "Software-Update",
        "description": "Update-Pakete einspielen, Backups verwalten, Update-Verlauf einsehen.",
        "detail":      "UPDATE_MANIFEST_URL · Backup-Verwaltung · Update-History",
        "action":      "navigate",
    },
    {
        "key":         "settings_system",
        "title":       "Systemparameter",
        "description": "Fallnummernpräfix und weitere applikationsweite Systemkonfiguration.",
        "detail":      "CASE_NUMBER_PREFIX · Systeminfo",
        "action":      "navigate",
    },
    {
        "key":         "open_manual",
        "title":       "Benutzerhandbuch",
        "description": "Vollständige Bedienungsanleitung im PDF-Format öffnen oder neu generieren.",
        "detail":      "Benutzerhandbuch.pdf · Alle 13 Kapitel · Automatisch generiert",
        "action":      "open_manual",
    },
]


class SettingsPage(QWidget):
    def __init__(self, settings_service: SettingsService | None = None,
                 navigate_callback=None, manual_service=None):
        super().__init__()
        self.settings_service = settings_service or SettingsService()
        self.navigate_callback = navigate_callback
        self._manual_service = manual_service
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("settingsPage")

        # Äusseres Layout: nur die ScrollArea
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        # Scrollbarer Inhaltsbereich
        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        root.addWidget(PageHeader(
            title="Einstellungen",
            subtitle="Wählen Sie eine Kategorie, um die jeweiligen Einstellungen zu bearbeiten.",
        ))

        # System-Info-Zeile
        info_row = QHBoxLayout()
        info_row.setSpacing(24)
        for label, value in [
            ("Angemeldeter Benutzer", Session.get_full_name() or "–"),
            ("Rolle",                 Session.get_role_name() or "–"),
            ("Version",               "1.0.0"),
        ]:
            col = QVBoxLayout()
            col.setSpacing(1)
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px; color: #888;")
            val = QLabel(value)
            val.setStyleSheet("font-size: 13px; font-weight: bold; color: #333;")
            col.addWidget(lbl)
            col.addWidget(val)
            info_row.addLayout(col)
        info_row.addStretch()
        root.addLayout(info_row)

        # Kategorie-Kacheln (2-spaltig, automatisch umbrechen)
        grid = QGridLayout()
        grid.setSpacing(16)

        for idx, cat in enumerate(_CATEGORIES):
            row, col = divmod(idx, 2)
            grid.addWidget(self._build_card(cat), row, col)

        root.addLayout(grid)
        root.addStretch()

        scroll.setWidget(content)

    def _build_card(self, cat: dict) -> QFrame:
        is_manual = cat.get("action") == "open_manual"

        card = QFrame()
        card.setObjectName("Card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        title = QLabel(cat["title"])
        title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1a1a1a;"
        )

        description = QLabel(cat["description"])
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; color: #555;")

        detail = QLabel(cat["detail"])
        detail.setWordWrap(True)
        detail.setStyleSheet(
            "font-size: 11px; color: #888; font-family: Consolas, monospace;"
        )

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(detail)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_open = QPushButton("Öffnen")
        btn_open.setObjectName("SoftButton")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedWidth(110)
        btn_open.clicked.connect(
            lambda checked=False, k=cat["key"], a=cat.get("action", "navigate"):
            self._handle_action(k, a)
        )
        btn_row.addWidget(btn_open)

        if is_manual:
            btn_regen = QPushButton("Neu erstellen")
            btn_regen.setObjectName("SoftButton")
            btn_regen.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_regen.setFixedWidth(110)
            btn_regen.clicked.connect(self._regenerate_manual)
            btn_row.addWidget(btn_regen)

        layout.addLayout(btn_row)
        return card

    def _handle_action(self, key: str, action: str) -> None:
        if action == "open_manual":
            self._open_manual()
        else:
            self._navigate(key)

    def _navigate(self, key: str) -> None:
        if self.navigate_callback:
            self.navigate_callback(key)

    def _open_manual(self) -> None:
        if self._manual_service is None:
            QMessageBox.warning(self, "Nicht verfügbar",
                                "Benutzerhandbuch-Service nicht konfiguriert.")
            return
        try:
            self._manual_service.open_manual()
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim Öffnen",
                                 f"Das Benutzerhandbuch konnte nicht geöffnet werden:\n{exc}")

    def _regenerate_manual(self) -> None:
        if self._manual_service is None:
            return
        try:
            self._manual_service.regenerate()
            QMessageBox.information(self, "Benutzerhandbuch",
                                    "Das Benutzerhandbuch wurde neu erstellt.\n"
                                    f"Pfad: {self._manual_service.get_path()}")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler",
                                 f"Handbuch konnte nicht erstellt werden:\n{exc}")
