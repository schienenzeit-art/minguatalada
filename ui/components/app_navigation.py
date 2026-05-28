from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt

from app.app_registry import AppRegistry
from core.session import Session

_PERSONAL_ROLES = {"Standortleitung", "Supervisor", "Admin"}


class AppNavigation(QWidget):
    def __init__(self, navigate_callback):
        super().__init__()
        self.navigate_callback = navigate_callback
        self.active_button = None
        self.buttons = {}
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("appNavigation")
        self.setMinimumWidth(248)
        self.setMaximumWidth(270)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 24, 16, 20)
        layout.setSpacing(2)

        title = QLabel("Anspruchs-Plattform")
        title.setObjectName("appNavTitle")
        layout.addWidget(title)

        subtitle = QLabel("Modulare Fachapplikationen")
        subtitle.setObjectName("appNavSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addSpacing(10)
        self.add_nav_item(layout, "Startcockpit", "dashboard")
        layout.addSpacing(8)

        section_label = QLabel("Applikationen")
        section_label.setObjectName("appNavSection")
        layout.addWidget(section_label)
        layout.addSpacing(2)

        for app in AppRegistry.get_visible_apps():
            self.add_nav_item(layout, app.title, app.page_key)

        # ── Personal-Bereich ──────────────────────────────────────────────────
        role_name = (Session.get_user() or {}).get("role_name", "")
        if role_name in _PERSONAL_ROLES:
            layout.addSpacing(10)
            personal_label = QLabel("Personal")
            personal_label.setObjectName("appNavSection")
            layout.addWidget(personal_label)
            layout.addSpacing(2)
            self.add_nav_item(layout, "  Geschäftsführung", "personal_management")
            self.add_nav_item(layout, "  Mitarbeiter", "personal_staff")
            self.add_nav_item(layout, "  Freiwillige", "personal_volunteers")

        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        user = Session.get_user() or {}
        user_name = user.get("full_name", "Unbekannter Benutzer")
        location_name = user.get("location_name", "-")
        role_name = user.get("role_name", "-")
        self.meta_label = QLabel(f"{user_name}\n{role_name} • {location_name}")
        self.meta_label.setObjectName("appNavMeta")
        self.meta_label.setWordWrap(True)
        layout.addWidget(self.meta_label)

        logout_button = QPushButton("Abmelden")
        logout_button.setObjectName("appNavLogout")
        logout_button.clicked.connect(lambda: self.navigate_callback("logout"))
        layout.addWidget(logout_button)

        self.setLayout(layout)

    def add_nav_item(self, layout, label: str, page_key: str):
        button = QPushButton(label)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setCheckable(True)
        button.clicked.connect(lambda: self.on_navigate(page_key))
        layout.addWidget(button)
        self.buttons[page_key] = button

    def on_navigate(self, page_key: str):
        self.set_active(page_key)
        self.navigate_callback(page_key)

    def set_active(self, page_key: str):
        if self.active_button:
            self.active_button.setChecked(False)
            self.active_button.setObjectName("")
            self.active_button.style().unpolish(self.active_button)
            self.active_button.style().polish(self.active_button)

        button = self.buttons.get(page_key)
        if button:
            button.setChecked(True)
            button.setObjectName("activeAppNav")
            self.active_button = button
            button.style().unpolish(button)
            button.style().polish(button)
