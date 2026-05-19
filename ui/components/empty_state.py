from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class EmptyState(QWidget):
    def __init__(self, title: str, message: str):
        super().__init__()
        self.title = title
        self.message = message
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("emptyState")
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title_label = QLabel(self.title)
        title_label.setObjectName("emptyStateTitle")
        description_label = QLabel(self.message)
        description_label.setObjectName("emptyStateMessage")
        description_label.setWordWrap(True)

        layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addStretch()

        self.setLayout(layout)
