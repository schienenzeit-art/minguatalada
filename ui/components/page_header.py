from typing import Callable

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt


class PageHeader(QWidget):
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        action_text: str | None = None,
        action_callback: Callable[[], None] | None = None,
    ):
        super().__init__()
        self.title = title
        self.subtitle = subtitle
        self.action_text = action_text
        self.action_callback = action_callback
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("pageHeader")
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title_box = QWidget()
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)

        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("pageHeaderTitle")
        self.subtitle_label = QLabel(self.subtitle)
        self.subtitle_label.setObjectName("pageHeaderSubtitle")
        self.subtitle_label.setWordWrap(True)

        title_layout.addWidget(self.title_label)
        if self.subtitle:
            title_layout.addWidget(self.subtitle_label)

        title_box.setLayout(title_layout)
        layout.addWidget(title_box)
        layout.addStretch()

        self.action_button = None
        if self.action_text:
            self.action_button = QPushButton(self.action_text)
            self.action_button.setObjectName("pageHeaderAction")
            self.action_button.setCursor(Qt.CursorShape.PointingHandCursor)
            if self.action_callback:
                self.action_button.clicked.connect(self.action_callback)
            layout.addWidget(self.action_button)

        self.setLayout(layout)
