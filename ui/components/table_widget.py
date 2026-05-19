from PyQt6.QtWidgets import QTableWidget


class TableWidget(QTableWidget):
    def __init__(self, columns: int = 0):
        super().__init__(0, columns)
        self.setObjectName("tableWidget")
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
