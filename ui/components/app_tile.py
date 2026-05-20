from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal


class AppTile(QWidget):
    clicked = pyqtSignal()

    def __init__(self, title: str, subtitle: str, accent: str = "#2383e2"):
        super().__init__()
        self.title = title
        self.subtitle = subtitle
        self.accent = accent
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("appTile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("accent", self.accent)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("appTileTitle")
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(self.subtitle)
        self.subtitle_label.setObjectName("appTileSubtitle")
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)

        self.setLayout(layout)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit()
