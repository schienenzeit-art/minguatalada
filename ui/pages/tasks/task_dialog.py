from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QDateEdit,
    QDialogButtonBox,
    QMessageBox,
)
from PyQt6.QtCore import QDate

from core.task_priority import TaskPriority
from core.task_status import TaskStatus
from core.task_type import TaskType
from core.task_source_type import TaskSourceType
from services.location_service import LocationService
from services.user_service import UserService


class TaskDialog(QDialog):
    def __init__(
        self,
        user_service: UserService,
        location_service: LocationService,
        task: dict | None = None,
        preset_type: str | None = None,
    ):
        super().__init__()
        self.user_service = user_service
        self.location_service = location_service
        self.task = task
        self.preset_type = preset_type
        self.setWindowTitle("Wiedervorlage" if preset_type == TaskType.WIEDERVORLAGE else "Aufgabe")
        self.setup_ui()
        self.load_task()

    def setup_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        self.title_input = QLineEdit()
        self.description_input = QTextEdit()
        self.type_input = QComboBox()
        self.type_input.addItems(TaskType.ALL_TYPES)
        self.status_input = QComboBox()
        self.status_input.addItems([TaskStatus.get_display(status) for status in TaskStatus.ALL_STATUSES])
        self.priority_input = QComboBox()
        self.priority_input.addItems([TaskPriority.get_display(priority) for priority in TaskPriority.ALL_PRIORITIES])
        self.due_date_input = QDateEdit()
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setDate(QDate.currentDate())

        self.assigned_user_input = QComboBox()
        self.assigned_user_input.addItem("Keine Zuordnung", None)
        for user in self.user_service.get_all_users():
            self.assigned_user_input.addItem(user["full_name"], user["id"])

        self.location_input = QComboBox()
        self.location_input.addItem("Kein Standort", None)
        for location in self.location_service.list_active_locations():
            self.location_input.addItem(location["name"], location["id"])

        self.source_type_input = QComboBox()
        self.source_type_input.addItems(["Keine", "Fall/Antrag", "Dokument", "Karte", "Standort"])
        self.source_ref_id_input = QLineEdit()
        self.source_description_input = QLineEdit()

        form.addRow("Betreff:", self.title_input)
        form.addRow("Notiz:", self.description_input)
        form.addRow("Typ:", self.type_input)
        form.addRow("Status:", self.status_input)
        form.addRow("Priorität:", self.priority_input)
        form.addRow("Fällig am:", self.due_date_input)
        form.addRow("Verantwortlich:", self.assigned_user_input)
        form.addRow("Standort:", self.location_input)
        form.addRow("Quelle:", self.source_type_input)
        form.addRow("Referenz-ID:", self.source_ref_id_input)
        form.addRow("Quelle Beschreibung:", self.source_description_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def load_task(self):
        if self.preset_type and not self.task:
            index = self.type_input.findText(self.preset_type)
            if index >= 0:
                self.type_input.setCurrentIndex(index)
            return
        if not self.task:
            return

        self.title_input.setText(self.task.get("title", ""))
        self.description_input.setPlainText(self.task.get("description", ""))
        task_type = self.task.get("task_type", "Allgemein")
        index = self.type_input.findText(task_type)
        if index >= 0:
            self.type_input.setCurrentIndex(index)

        status = TaskStatus.get_display(self.task.get("status", TaskStatus.OFFEN))
        index = self.status_input.findText(status)
        if index >= 0:
            self.status_input.setCurrentIndex(index)

        priority = TaskPriority.get_display(self.task.get("priority", TaskPriority.MITTEL))
        index = self.priority_input.findText(priority)
        if index >= 0:
            self.priority_input.setCurrentIndex(index)

        due_date = self.task.get("due_date")
        if due_date:
            self.due_date_input.setDate(QDate.fromString(due_date, "yyyy-MM-dd"))

        assigned = self.task.get("assigned_user_id")
        if assigned:
            index = self.assigned_user_input.findData(assigned)
            if index >= 0:
                self.assigned_user_input.setCurrentIndex(index)

        location_id = self.task.get("location_id")
        if location_id:
            index = self.location_input.findData(location_id)
            if index >= 0:
                self.location_input.setCurrentIndex(index)

        source_type = self.task.get("source_ref_type")
        if source_type:
            display = {
                "claim": "Fall/Antrag",
                "document": "Dokument",
                "card": "Karte",
                "location": "Standort",
            }.get(source_type, "Keine")
            index = self.source_type_input.findText(display)
            if index >= 0:
                self.source_type_input.setCurrentIndex(index)

        if self.task.get("source_ref_id") is not None:
            self.source_ref_id_input.setText(str(self.task.get("source_ref_id")))

        self.source_description_input.setText(self.task.get("source_description", ""))

    def get_data(self) -> dict:
        source_type = self.source_type_input.currentText()
        source_ref_type = None
        if source_type == "Fall/Antrag":
            source_ref_type = "claim"
        elif source_type == "Dokument":
            source_ref_type = "document"
        elif source_type == "Karte":
            source_ref_type = "card"
        elif source_type == "Standort":
            source_ref_type = "location"

        source_type_value = TaskSourceType.MANUAL if source_ref_type else "manual"

        source_ref_id = self.source_ref_id_input.text().strip()
        return {
            "title": self.title_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "task_type": self.type_input.currentText(),
            "status": TaskStatus.ALL_STATUSES[self.status_input.currentIndex()],
            "priority": TaskPriority.ALL_PRIORITIES[self.priority_input.currentIndex()],
            "due_date": self.due_date_input.date().toString("yyyy-MM-dd"),
            "assigned_user_id": self.assigned_user_input.currentData(),
            "location_id": self.location_input.currentData(),
            "source_type": source_type_value,
            "source_ref_type": source_ref_type,
            "source_ref_id": int(source_ref_id) if source_ref_id.isdigit() else None,
            "source_description": self.source_description_input.text().strip(),
        }

    def accept(self) -> None:
        data = self.get_data()
        if not data["title"]:
            QMessageBox.warning(self, "Fehler", "Betreff ist erforderlich.")
            return
        super().accept()
