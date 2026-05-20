from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt

from app.app_registry import AppRegistry
from core.session import Session


class Sidebar(QWidget):
    def __init__(self, navigate_callback):
        super().__init__()
        self.navigate_callback = navigate_callback
        self.active_button = None
        self.buttons = {}
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("sidebar")
        self.setMinimumWidth(240)
        self.setMaximumWidth(240)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        logo = QLabel("Anspruchssystem")
        logo.setObjectName("sidebarLogo")
        logo.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(logo)

        self.add_nav_item(layout, "Dashboard", "dashboard")

        app_title = QLabel("Applikationen")
        app_title.setObjectName("sidebarSectionTitle")
        layout.addWidget(app_title)

        for app in AppRegistry.get_visible_apps():
            self.add_nav_item(layout, app.title, app.page_key)

        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        user = Session.get_user() or {}
        user_name = user.get("full_name", "Unbekannter Benutzer")
        role_name = user.get("role_name", "-")
        location_name = user.get("location_name", "-")
        self.meta_label = QLabel(f"{user_name}\n{role_name} • {location_name}")
        self.meta_label.setObjectName("sidebarMeta")
        self.meta_label.setWordWrap(True)
        layout.addWidget(self.meta_label)

        logout_button = QPushButton("Abmelden")
        logout_button.setObjectName("logoutButton")
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
            button.setObjectName("activeNav")
            self.active_button = button
            button.style().unpolish(button)
            button.style().polish(button)
