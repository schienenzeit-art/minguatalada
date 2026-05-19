from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt


class TopBar(QWidget):
    def __init__(self, title: str = "Dashboard"):
        super().__init__()
        self.title = title
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("topBar")
        layout = QHBoxLayout()
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(14)

        self.page_title = QLabel(self.title)
        self.page_title.setObjectName("pageTitle")
        self.page_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Suche...")
        self.search_input.setObjectName("topbarSearch")
        self.search_input.setMaximumWidth(320)

        self.notification_button = QPushButton("Benachrichtigungen")
        self.notification_button.setObjectName("topbarButton")
        self.notification_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.avatar_button = QPushButton("Benutzer")
        self.avatar_button.setObjectName("topbarButton")
        self.avatar_button.setCursor(Qt.CursorShape.PointingHandCursor)

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

    def set_title(self, title: str) -> None:
        self.page_title.setText(title)
