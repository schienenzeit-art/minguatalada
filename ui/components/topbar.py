from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMenu, QFrame, QVBoxLayout, QScrollArea, QSizePolicy,
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QTimer


class TopBar(QWidget):
    user_changed      = pyqtSignal(dict)
    search_requested  = pyqtSignal(str)
    notification_read = pyqtSignal(int)

    def __init__(self, title: str = "Dashboard", current_user: dict | None = None):
        super().__init__()
        self.title           = title
        self.current_user    = current_user
        self.available_users = []
        self._notification_service = None
        self._unread_count   = 0
        self.setup_ui()

    # ── UI-Aufbau ─────────────────────────────────────────────────────────────
    def setup_ui(self):
        self.setObjectName("topBar")
        self.setMinimumHeight(58)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 10, 20, 10)
        layout.setSpacing(10)

        self.page_title = QLabel(self.title)
        self.page_title.setObjectName("pageTitle")
        self.page_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Suche …")
        self.search_input.setObjectName("topbarSearch")
        self.search_input.setMaximumWidth(300)
        self.search_input.returnPressed.connect(self._on_search)

        # ── Benachrichtigungs-Bell ─────────────────────────────────────────────
        self.bell_button = QPushButton("🔔")
        self.bell_button.setObjectName("topbarButton")
        self.bell_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bell_button.setFixedSize(38, 38)
        self.bell_button.setToolTip("Benachrichtigungen")
        self.bell_button.clicked.connect(self._show_notifications)

        self._badge = QLabel("0")
        self._badge.setFixedSize(18, 18)
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setStyleSheet(
            "background: #d1495b; color: #fff; border-radius: 9px; "
            "font-size: 10px; font-weight: 800;"
        )
        self._badge.hide()

        bell_container = QWidget()
        bell_container.setFixedSize(44, 44)
        bell_container.setStyleSheet("background: transparent;")
        bell_layout = QVBoxLayout(bell_container)
        bell_layout.setContentsMargins(0, 0, 0, 0)
        bell_layout.setSpacing(0)

        # Badge overlay via fixed positioning — simpler: use the button text
        bell_layout.addWidget(self.bell_button)

        # ── Benutzer-Button ────────────────────────────────────────────────────
        self.avatar_button = QPushButton(self._get_user_display_name())
        self.avatar_button.setObjectName("topbarButton")
        self.avatar_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avatar_button.clicked.connect(self._show_user_menu)

        layout.addWidget(self.page_title)
        layout.addStretch()
        layout.addWidget(self.search_input)
        layout.addWidget(self.bell_button)
        layout.addWidget(self.avatar_button)

    # ── Notification-Service binden ───────────────────────────────────────────
    def set_notification_service(self, svc) -> None:
        self._notification_service = svc
        # Poll für Badge-Update alle 60 Sekunden
        timer = QTimer(self)
        timer.timeout.connect(self._refresh_badge)
        timer.start(60_000)
        self._refresh_badge()

    def _refresh_badge(self) -> None:
        if self._notification_service is None:
            return
        try:
            count = self._notification_service.count_unread()
        except Exception:
            count = 0
        self._unread_count = count
        if count > 0:
            self.bell_button.setText(f"🔔 {count}")
            self.bell_button.setStyleSheet(
                "background: #fde8e8; color: #c0362a; border: 1.5px solid #fad0cd; "
                "border-radius: 10px; font-weight: 700; font-size: 12px;"
            )
        else:
            self.bell_button.setText("🔔")
            self.bell_button.setStyleSheet("")

    # ── Notifications-Dropdown ────────────────────────────────────────────────
    def _show_notifications(self) -> None:
        menu = QMenu(self)
        menu.setMinimumWidth(340)

        if self._notification_service is None:
            menu.addAction("Kein Benachrichtigungsdienst verfügbar").setEnabled(False)
            menu.exec(self.bell_button.mapToGlobal(self.bell_button.rect().bottomLeft()))
            return

        notifications = self._notification_service.get_notifications(limit=20)
        if not notifications:
            menu.addAction("Keine Benachrichtigungen").setEnabled(False)
        else:
            for n in notifications:
                text  = n.get("title", "")
                msg   = n.get("message", "")
                label = f"{text}" + (f"\n  {msg}" if msg else "")
                is_read = bool(n.get("is_read"))
                action = QAction(label, menu)
                if not is_read:
                    font = action.font()
                    font.setBold(True)
                    action.setFont(font)
                nid = n["id"]
                action.triggered.connect(
                    lambda checked=False, _id=nid: self._on_notification_click(_id)
                )
                menu.addAction(action)

            menu.addSeparator()
            mark_all = menu.addAction("Alle als gelesen markieren")
            mark_all.triggered.connect(self._mark_all_read)

        menu.exec(self.bell_button.mapToGlobal(self.bell_button.rect().bottomLeft()))

    def _on_notification_click(self, notification_id: int) -> None:
        if self._notification_service:
            self._notification_service.mark_read(notification_id)
            self._refresh_badge()
        self.notification_read.emit(notification_id)

    def _mark_all_read(self) -> None:
        if self._notification_service:
            self._notification_service.mark_all_read()
            self._refresh_badge()

    # ── Benutzerwechsel ───────────────────────────────────────────────────────
    def _get_user_display_name(self) -> str:
        if self.current_user:
            return self.current_user.get("full_name", "Benutzer")[:22]
        return "Benutzer"

    def set_current_user(self, user: dict) -> None:
        self.current_user = user
        self.avatar_button.setText(self._get_user_display_name())

    def set_available_users(self, users: list[dict]) -> None:
        self.available_users = users

    def _show_user_menu(self) -> None:
        if not self.available_users:
            return
        menu = QMenu(self)
        for user in self.available_users:
            action = menu.addAction(user.get("full_name", user.get("username", "-")))
            action.triggered.connect(lambda checked=False, u=user: self._switch_user(u))
        menu.addSeparator()
        menu.addAction("Abmelden").triggered.connect(self._on_logout)
        menu.exec(self.avatar_button.mapToGlobal(self.avatar_button.rect().bottomLeft()))

    def _switch_user(self, user: dict) -> None:
        self.set_current_user(user)
        self.user_changed.emit(user)

    def _on_logout(self) -> None:
        self.user_changed.emit({"logout": True})

    def _on_search(self) -> None:
        text = self.search_input.text().strip()
        if text:
            self.search_requested.emit(text)

    def set_title(self, title: str) -> None:
        self.page_title.setText(title)
