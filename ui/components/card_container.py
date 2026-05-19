from PyQt6.QtWidgets import QWidget, QVBoxLayout


class CardContainer(QWidget):
    def __init__(self, *cards):
        super().__init__()
        self.cards = cards
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("cardContainer")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        for card in self.cards:
            layout.addWidget(card)
        layout.addStretch()
        self.setLayout(layout)
