from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class StatCard(QWidget):
    clicked = pyqtSignal()

    def __init__(self, title: str, value: str, subtitle: str, accent: str = "#2383e2"):
        super().__init__()
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.accent = accent
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("statCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("statCardTitle")
        self.value_label = QLabel(self.value)
        self.value_label.setObjectName("statCardValue")
        self.subtitle_label = QLabel(self.subtitle)
        self.subtitle_label.setObjectName("statCardSubtitle")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)
        layout.addStretch()

        self.setLayout(layout)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def set_value(self, value: str) -> None:
        self.value = value
        self.value_label.setText(value)
