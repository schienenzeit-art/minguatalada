from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class AppCard(QWidget):
    clicked = pyqtSignal()

    def __init__(self, title: str, subtitle: str, accent: str = "#2383e2"):
        super().__init__()
        self.title = title
        self.subtitle = subtitle
        self.accent = accent
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("appCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title_label = QLabel(self.title)
        title_label.setObjectName("appCardTitle")

        subtitle_label = QLabel(self.subtitle)
        subtitle_label.setObjectName("appCardSubtitle")
        subtitle_label.setWordWrap(True)
        subtitle_label.setMaximumWidth(320)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addStretch()

        self.setLayout(layout)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)
