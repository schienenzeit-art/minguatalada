from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMenu
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal


class TopBar(QWidget):
    user_changed = pyqtSignal(dict)  # Emits dict with user info
    search_requested = pyqtSignal(str)  # Emits search text

    def __init__(self, title: str = "Dashboard", current_user: dict | None = None):
        super().__init__()
        self.title = title
        self.current_user = current_user
        self.available_users = []  # Will be populated by MainWindow
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("topBar")
        self.setMinimumHeight(58)
        layout = QHBoxLayout()
        layout.setContentsMargins(24, 10, 20, 10)
        layout.setSpacing(10)

        self.page_title = QLabel(self.title)
        self.page_title.setObjectName("pageTitle")
        self.page_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Suche...")
        self.search_input.setObjectName("topbarSearch")
        self.search_input.setMaximumWidth(320)
        self.search_input.returnPressed.connect(self._on_search)

        self.notification_button = QPushButton("Benachrichtigungen")
        self.notification_button.setObjectName("topbarButton")
        self.notification_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.avatar_button = QPushButton(self._get_user_display_name())
        self.avatar_button.setObjectName("topbarButton")
        self.avatar_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avatar_button.clicked.connect(self._show_user_menu)

        self.theme_button = QPushButton("Theme")
        self.theme_button.setObjectName("topbarButton")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(self.page_title)
        layout.addStretch()
        layout.addWidget(self.search_input)
        layout.addWidget(self.notification_button)
        layout.addWidget(self.avatar_button)
        layout.addWidget(self.theme_button)

        self.setLayout(layout)

    def _get_user_display_name(self) -> str:
        """Get display name for avatar button."""
        if self.current_user:
            return self.current_user.get("full_name", "Benutzer")[:20]  # Truncate long names
        return "Benutzer"

    def set_current_user(self, user: dict) -> None:
        """Update current user and button label."""
        self.current_user = user
        self.avatar_button.setText(self._get_user_display_name())

    def set_available_users(self, users: list[dict]) -> None:
        """Set list of users for switching."""
        self.available_users = users

    def _show_user_menu(self) -> None:
        """Show dropdown menu with available users."""
        if not self.available_users:
            return

        menu = QMenu(self)
        for user in self.available_users:
            action = menu.addAction(user.get("full_name", user.get("username", "-")))
            action.triggered.connect(lambda checked=False, u=user: self._switch_user(u))

        menu.addSeparator()
        logout_action = menu.addAction("Abmelden")
        logout_action.triggered.connect(self._on_logout)

        # Show menu at button position
        button_rect = self.avatar_button.geometry()
        menu_pos = self.mapToGlobal(button_rect.bottomLeft())
        menu.exec(menu_pos)

    def _switch_user(self, user: dict) -> None:
        """Emit signal to switch user."""
        self.set_current_user(user)
        self.user_changed.emit(user)

    def _on_logout(self) -> None:
        """Handle logout (will be connected to main window)."""
        self.user_changed.emit({"logout": True})

    def _on_search(self) -> None:
        """Emit search signal when user presses Enter."""
        search_text = self.search_input.text().strip()
        if search_text:
            self.search_requested.emit(search_text)

    def set_title(self, title: str) -> None:
        self.page_title.setText(title)
