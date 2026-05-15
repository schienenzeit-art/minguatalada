from PyQt6.QtWidgets import QMainWindow, QLabel

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Anspruchssystem")
        self.setCentralWidget(QLabel("Woche 1 Grundgerüst läuft."))