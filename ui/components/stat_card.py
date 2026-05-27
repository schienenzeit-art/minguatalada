from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QSizePolicy, QVBoxLayout, QWidget


class StatCard(QWidget):
    clicked = pyqtSignal()

    def __init__(self, title: str, value: str, subtitle: str, accent: str = "#2383e2"):
        super().__init__()
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.accent = accent
        self.setup_ui()
        self._apply_shadow()

    def setup_ui(self):
        self.setObjectName("statCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(138)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Farbiger Akzent-Strip oben
        accent_strip = QFrame()
        accent_strip.setFixedHeight(5)
        accent_strip.setStyleSheet(
            f"background-color: {self.accent}; border-radius: 16px 16px 0 0; border: none;"
        )
        outer.addWidget(accent_strip)

        # Inhalt
        content = QWidget()
        content.setObjectName("statCardInner")
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(4)

        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("statCardTitle")
        self.title_label.setMinimumHeight(18)

        self.value_label = QLabel(self.value)
        self.value_label.setObjectName("statCardValue")
        self.value_label.setMinimumHeight(44)
        self.value_label.setStyleSheet(
            f"color: {self.accent}; font-size: 32px; font-weight: 800; letter-spacing: -0.04em;"
        )

        self.subtitle_label = QLabel(self.subtitle)
        self.subtitle_label.setObjectName("statCardSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setMinimumHeight(18)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addSpacing(2)
        layout.addWidget(self.subtitle_label)
        layout.addStretch()

        outer.addWidget(content)

    def _apply_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 18))
        self.setGraphicsEffect(shadow)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def set_value(self, value: str) -> None:
        self.value = value
        self.value_label.setText(value)
