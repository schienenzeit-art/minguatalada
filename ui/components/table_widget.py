from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidget, QHeaderView


class TableWidget(QTableWidget):
    def __init__(self, columns: int = 0):
        super().__init__(0, columns)
        self.setObjectName("tableWidget")
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWordWrap(False)
        self.setCornerButtonEnabled(False)
        self.setContentsMargins(0, 0, 0, 0)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(56)
        self.verticalHeader().setMinimumSectionSize(48)
        header = self.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(80)
        header.setDefaultSectionSize(120)
