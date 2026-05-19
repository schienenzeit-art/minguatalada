from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)

from core.session import Session
from core.task_priority import TaskPriority
from core.task_status import TaskStatus
from services.task_service import TaskService
from services.user_service import UserService
from services.location_service import LocationService
from ui.components.page_header import PageHeader
from ui.pages.claim_detail_page import ClaimDetailPage
from ui.pages.tasks.task_dialog import TaskDialog


class TasksPage(QWidget):
    def __init__(
        self,
        task_service: TaskService | None = None,
        user_service: UserService | None = None,
        location_service: LocationService | None = None,
        navigate_callback=None,
    ):
        super().__init__()
        self.task_service = task_service or TaskService()
        self.user_service = user_service or UserService()
        self.location_service = location_service or LocationService()
        self.navigate_callback = navigate_callback
        self.tasks: list[dict] = []
        self.setup_ui()
        self.load_filters()
        self.refresh_tasks()

    def setup_ui(self):
        self.setObjectName("tasksPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = PageHeader(
            title="Actionboard",
            subtitle="Operative Aufgabenliste für manuelle und systemgenerierte Aufgaben",
            action_text="Neue Aufgabe",
            action_callback=self.open_new_task_dialog,
        )
        layout.addWidget(header)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Suche nach Betreff, Notiz oder Quelle")
        self.search_input.textChanged.connect(self.refresh_tasks)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Alle Status", None)
        for status in TaskStatus.ALL_STATUSES:
            self.status_combo.addItem(TaskStatus.get_display(status), status)
        self.status_combo.currentIndexChanged.connect(self.refresh_tasks)

        self.priority_combo = QComboBox()
        self.priority_combo.addItem("Alle Prioritäten", None)
        for priority in TaskPriority.ALL_PRIORITIES:
            self.priority_combo.addItem(TaskPriority.get_display(priority), priority)
        self.priority_combo.currentIndexChanged.connect(self.refresh_tasks)

        self.assigned_user_combo = QComboBox()
        self.assigned_user_combo.addItem("Alle Verantwortlichen", None)
        self.assigned_user_combo.currentIndexChanged.connect(self.refresh_tasks)

        self.location_combo = QComboBox()
        self.location_combo.addItem("Alle Standorte", None)
        self.location_combo.currentIndexChanged.connect(self.refresh_tasks)

        self.mine_only_checkbox = QCheckBox("Nur meine Aufgaben")
        self.mine_only_checkbox.setChecked(not Session.is_admin())
        self.mine_only_checkbox.stateChanged.connect(self.refresh_tasks)

        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.status_combo)
        filter_layout.addWidget(QLabel("Priorität:"))
        filter_layout.addWidget(self.priority_combo)
        filter_layout.addWidget(QLabel("Verantwortlich:"))
        filter_layout.addWidget(self.assigned_user_combo)
        filter_layout.addWidget(QLabel("Standort:"))
        filter_layout.addWidget(self.location_combo)
        filter_layout.addWidget(self.mine_only_checkbox)
        layout.addLayout(filter_layout)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "Status",
            "Betreff",
            "Typ",
            "Priorität",
            "Fällig am",
            "Verantwortlich",
            "Standort",
            "Quelle",
            "Systemaufgabe",
            "Aktion",
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)
        layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        refresh_button = QPushButton("Aktualisieren")
        refresh_button.clicked.connect(self.refresh_tasks)
        self.complete_button = QPushButton("Als erledigt markieren")
        self.complete_button.clicked.connect(self.mark_selected_task_done)
        self.complete_button.setEnabled(False)
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(self.complete_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

    def load_filters(self):
        self.assigned_user_combo.clear()
        self.assigned_user_combo.addItem("Alle Verantwortlichen", None)
        for user in self.user_service.get_all_users():
            self.assigned_user_combo.addItem(user["full_name"], user["id"])

        self.location_combo.clear()
        self.location_combo.addItem("Alle Standorte", None)
        for location in self.location_service.list_active_locations():
            self.location_combo.addItem(location["name"], location["id"])

    def refresh_tasks(self):
        status = self.status_combo.currentData()
        priority = self.priority_combo.currentData()
        assigned_user_id = self.assigned_user_combo.currentData()
        location_id = self.location_combo.currentData()
        mine_only = self.mine_only_checkbox.isChecked()
        search_text = self.search_input.text().strip() or None

        self.tasks = self.task_service.list_tasks(
            status=status,
            priority=priority,
            assigned_user_id=assigned_user_id,
            location_id=location_id,
            mine_only=mine_only,
            search_text=search_text,
        )
        self.render_table()

    def render_table(self):
        self.table.setRowCount(len(self.tasks))

        for row_index, task in enumerate(self.tasks):
            self.table.setItem(row_index, 0, QTableWidgetItem(TaskStatus.get_display(task["status"])))
            self.table.setItem(row_index, 1, QTableWidgetItem(task["title"]))
            self.table.setItem(row_index, 2, QTableWidgetItem(task.get("task_type", "")))
            self.table.setItem(row_index, 3, QTableWidgetItem(TaskPriority.get_display(task.get("priority", ""))))
            self.table.setItem(row_index, 4, QTableWidgetItem(task.get("due_date") or "-"))
            self.table.setItem(row_index, 5, QTableWidgetItem(task.get("assigned_user_name", "-")))
            self.table.setItem(row_index, 6, QTableWidgetItem(task.get("location_name", "-")))
            source_text = task.get("source_description") or task.get("source_ref_type", "-")
            self.table.setItem(row_index, 7, QTableWidgetItem(source_text))
            self.table.setItem(row_index, 8, QTableWidgetItem("Ja" if task.get("is_system_task") else "Nein"))

            action_button = QPushButton("Öffnen")
            action_button.clicked.connect(lambda _, t=task: self.open_task_source(t))
            if not task.get("is_system_task") and task.get("status") != TaskStatus.ERLEDIGT:
                complete_button = QPushButton("Erledigen")
                complete_button.clicked.connect(lambda _, t=task: self.complete_task(t))
                action_widget = QWidget()
                action_layout = QHBoxLayout()
                action_layout.setContentsMargins(0, 0, 0, 0)
                action_layout.setSpacing(6)
                action_layout.addWidget(action_button)
                action_layout.addWidget(complete_button)
                action_widget.setLayout(action_layout)
                self.table.setCellWidget(row_index, 9, action_widget)
            else:
                self.table.setCellWidget(row_index, 9, action_button)

        self.complete_button.setEnabled(False)

    def on_selection_changed(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            self.complete_button.setEnabled(False)
            return

        row = selected[0].row()
        task = self.tasks[row]
        self.complete_button.setEnabled(
            not task.get("is_system_task") and task.get("status") != TaskStatus.ERLEDIGT
        )

    def on_row_double_clicked(self, row: int, column: int):
        task = self.tasks[row]
        if task.get("is_system_task"):
            self.open_task_source(task)
            return

        self.open_edit_task_dialog(task)

    def open_new_task_dialog(self):
        dialog = TaskDialog(self.user_service, self.location_service)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.task_service.create_task(**data)
            self.refresh_tasks()

    def open_edit_task_dialog(self, task: dict):
        dialog = TaskDialog(self.user_service, self.location_service, task=task)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.task_service.update_task(task_id=task["id"], **data)
            self.refresh_tasks()

    def open_task_source(self, task: dict):
        ref_type = task.get("source_ref_type")
        ref_id = task.get("source_ref_id")

        if ref_type == "claim" and ref_id is not None:
            dialog = ClaimDetailPage(claim_id=ref_id)
            dialog.exec()
            return

        if self.navigate_callback:
            if ref_type == "card":
                self.navigate_callback("cards", filter_context={"search_text": str(ref_id)})
                return
            if ref_type == "document":
                self.navigate_callback("documents")
                return
            if ref_type == "location":
                self.navigate_callback("locations")
                return

        QMessageBox.information(self, "Quelle öffnen", "Die Aufgabe kann nicht direkt geöffnet werden.")

    def complete_task(self, task: dict):
        if task.get("is_system_task"):
            return
        if self.task_service.mark_task_completed(task["id"]):
            self.refresh_tasks()

    def mark_selected_task_done(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            return
        task = self.tasks[selected[0].row()]
        self.complete_task(task)

    def apply_filters(
        self,
        status: str | None = None,
        assigned_user_id: int | None = None,
        location_id: int | None = None,
        mine_only: bool = True,
    ) -> None:
        if status:
            for index in range(self.status_combo.count()):
                if self.status_combo.itemData(index) == status:
                    self.status_combo.setCurrentIndex(index)
                    break

        if assigned_user_id is not None:
            for index in range(self.assigned_user_combo.count()):
                if self.assigned_user_combo.itemData(index) == assigned_user_id:
                    self.assigned_user_combo.setCurrentIndex(index)
                    break

        if location_id is not None:
            for index in range(self.location_combo.count()):
                if self.location_combo.itemData(index) == location_id:
                    self.location_combo.setCurrentIndex(index)
                    break

        self.mine_only_checkbox.setChecked(mine_only)
        self.refresh_tasks()
