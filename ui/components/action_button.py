from PyQt6.QtWidgets import QPushButton


class ActionButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setObjectName("actionButton")
        self.setCursor(self.cursor())
        self.setMinimumHeight(42)
