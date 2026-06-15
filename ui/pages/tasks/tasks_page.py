from datetime import date as _date

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QTabWidget,
    QScrollArea,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)
from ui.components.table_widget import TableWidget

from core.session import Session
from core.task_priority import TaskPriority
from core.task_status import TaskStatus
from core.task_type import TaskType
from services.task_service import TaskService
from services.user_service import UserService
from services.location_service import LocationService
from services.service_factory import make_task_service
from ui.components.page_header import PageHeader
from ui.pages.claim_detail_page import ClaimDetailPage
from ui.pages.tasks.task_dialog import TaskDialog


# ─── Farb-Mapping für Priorität ──────────────────────────────────────────────
_PRIORITY_COLORS = {
    TaskPriority.KRITISCH: ("#fde8e8", "#c0362a", "Kritisch"),
    TaskPriority.HOCH:     ("#fff3e0", "#d46b00", "Hoch"),
    TaskPriority.MITTEL:   ("#e8f4fd", "#1762b5", "Mittel"),
    TaskPriority.NIEDRIG:  ("#f0faf3", "#14694d", "Niedrig"),
}


def _priority_badge(priority: str) -> QLabel:
    bg, fg, text = _PRIORITY_COLORS.get(priority, ("#f3f3f2", "#6b6860", priority or "-"))
    badge = QLabel(text)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setStyleSheet(
        f"background-color: {bg}; color: {fg}; border-radius: 10px; "
        f"padding: 2px 10px; font-size: 11px; font-weight: 700;"
    )
    return badge


def _status_badge(status: str) -> QLabel:
    mapping = {
        TaskStatus.OFFEN:         ("#fef8ec", "#886020", "Offen"),
        TaskStatus.IN_BEARBEITUNG:("#eef4ff", "#1762b5", "In Bearbeitung"),
        TaskStatus.WARTET:        ("#f3f3f2", "#6b6860", "Wartet"),
        TaskStatus.ERLEDIGT:      ("#f0faf3", "#14694d", "Erledigt"),
    }
    bg, fg, text = mapping.get(status, ("#f3f3f2", "#6b6860", status or "-"))
    badge = QLabel(text)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setStyleSheet(
        f"background-color: {bg}; color: {fg}; border-radius: 10px; "
        f"padding: 2px 10px; font-size: 11px; font-weight: 700;"
    )
    return badge


# ─── Kompakte KPI-Kachel für den Summary-Strip ───────────────────────────────
class _KpiChip(QFrame):
    def __init__(self, label: str, value: str, accent: str = "#2383e2"):
        super().__init__()
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(72)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 14))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(2)

        val_lbl = QLabel(value)
        val_lbl.setObjectName("_kpiChipValue")
        val_lbl.setStyleSheet(
            f"font-size: 22px; font-weight: 800; color: {accent}; letter-spacing: -0.03em;"
        )

        lbl = QLabel(label)
        lbl.setObjectName("_kpiChipLabel")
        lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #9b9896; text-transform: uppercase; letter-spacing: 0.05em;")

        layout.addWidget(val_lbl)
        layout.addWidget(lbl)

        self._val_lbl = val_lbl

    def set_value(self, v: str) -> None:
        self._val_lbl.setText(v)


class TasksPage(QWidget):
    def __init__(
        self,
        task_service: TaskService | None = None,
        user_service: UserService | None = None,
        location_service: LocationService | None = None,
        claim_service=None,
        navigate_callback=None,
    ):
        super().__init__()
        self.task_service = task_service or make_task_service()
        self.user_service = user_service or UserService()
        self.location_service = location_service or LocationService()
        self.claim_service = claim_service
        self.navigate_callback = navigate_callback
        self.tasks: list[dict] = []
        self.wiedervorlagen: list[dict] = []
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
            subtitle="Aufgaben, Wiedervorlagen und Fristen — nach Status, Priorität und Fälligkeit.",
            action_text="Neue Aufgabe",
            action_callback=self.open_new_task_dialog,
        )
        layout.addWidget(header)

        # ── KPI-Strip ────────────────────────────────────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        self._chip_open   = _KpiChip("Offene Aufgaben",       "–", "#d1495b")
        self._chip_over   = _KpiChip("Überfällig",            "–", "#e67e22")
        self._chip_today  = _KpiChip("Heute fällig",          "–", "#f39c12")
        self._chip_wv     = _KpiChip("Wiedervorlagen offen",  "–", "#2383e2")
        for chip in (self._chip_open, self._chip_over, self._chip_today, self._chip_wv):
            kpi_row.addWidget(chip)
        layout.addLayout(kpi_row)

        # ── Filter-Zeile ─────────────────────────────────────────────────────
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
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

        self.task_type_combo = QComboBox()
        self.task_type_combo.addItem("Alle Typen", None)
        for task_type in TaskType.ALL_TYPES:
            self.task_type_combo.addItem(TaskType.get_display(task_type), task_type)
        self.task_type_combo.currentIndexChanged.connect(self.refresh_tasks)

        self.source_combo = QComboBox()
        self.source_combo.addItem("Alle Quellen", None)
        self.source_combo.addItem("Manuell", "manual")
        self.source_combo.addItem("System", "system")
        self.source_combo.currentIndexChanged.connect(self.refresh_tasks)

        self.due_combo = QComboBox()
        self.due_combo.addItem("Alle Aufgaben", None)
        self.due_combo.addItem("Heute fällig", "today")
        self.due_combo.addItem("Überfällig", "overdue")
        self.due_combo.currentIndexChanged.connect(self.refresh_tasks)

        self.assigned_user_combo = QComboBox()
        self.assigned_user_combo.addItem("Alle Verantwortlichen", None)
        self.assigned_user_combo.currentIndexChanged.connect(self.refresh_tasks)

        self.location_combo = QComboBox()
        self.location_combo.addItem("Alle Standorte", None)
        self.location_combo.currentIndexChanged.connect(self.refresh_tasks)

        self.mine_only_checkbox = QCheckBox("Nur meine")
        self.mine_only_checkbox.setChecked(not Session.is_admin())
        self.mine_only_checkbox.stateChanged.connect(self.refresh_tasks)

        for w in [
            self.search_input,
            QLabel("Status:"), self.status_combo,
            QLabel("Typ:"), self.task_type_combo,
            QLabel("Priorität:"), self.priority_combo,
            QLabel("Quelle:"), self.source_combo,
            QLabel("Fällig:"), self.due_combo,
            QLabel("Verantw.:"), self.assigned_user_combo,
            QLabel("Standort:"), self.location_combo,
            self.mine_only_checkbox,
        ]:
            filter_layout.addWidget(w)
        layout.addLayout(filter_layout)

        # ── Tab-Widget: Alle Aufgaben | Wiedervorlagen ───────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.table = self._build_task_table()
        self.tabs.addTab(self.table, "Alle Aufgaben")

        self.wv_table = self._build_task_table(columns=8, extra_col="Typ")
        self.tabs.addTab(self.wv_table, "Wiedervorlagen")

        layout.addWidget(self.tabs)

        # ── Aktions-Buttons ──────────────────────────────────────────────────
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        refresh_button = QPushButton("Aktualisieren")
        refresh_button.clicked.connect(self.refresh_tasks)
        self.delegate_button = QPushButton("Delegieren …")
        self.delegate_button.clicked.connect(self.delegate_selected_task)
        self.delegate_button.setEnabled(False)
        self.complete_button = QPushButton("Als erledigt markieren")
        self.complete_button.clicked.connect(self.mark_selected_task_done)
        self.complete_button.setEnabled(False)
        wv_btn = QPushButton("Neue Wiedervorlage")
        wv_btn.setObjectName("SoftButton")
        wv_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        wv_btn.clicked.connect(self.open_new_wiedervorlage_dialog)
        button_layout.addWidget(wv_btn)
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(self.delegate_button)
        button_layout.addWidget(self.complete_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.wv_table.selectionModel().selectionChanged.connect(self.on_selection_changed)

    # ─── Tabellen-Konstruktor ─────────────────────────────────────────────────
    def _build_task_table(self, columns: int = 8, extra_col: str | None = None) -> TableWidget:
        cols = ["Status", "Betreff", "Priorität", "Fällig am", "Verantwortlich", "Standort", "Quelle", "Systemaufg."]
        if extra_col:
            cols.insert(2, extra_col)
        t = TableWidget(len(cols))
        t.setObjectName("dataTable")
        t.setHorizontalHeaderLabels(cols)
        t.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        t.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.cellDoubleClicked.connect(self.on_row_double_clicked)
        return t

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
        status            = self.status_combo.currentData()
        priority          = self.priority_combo.currentData()
        task_type         = self.task_type_combo.currentData()
        source_type       = self.source_combo.currentData()
        due_date_scope    = self.due_combo.currentData()
        assigned_user_id  = self.assigned_user_combo.currentData()
        location_id       = self.location_combo.currentData()
        mine_only         = self.mine_only_checkbox.isChecked()
        search_text       = self.search_input.text().strip() or None

        self.tasks = self.task_service.list_tasks(
            status=status, priority=priority, task_type=task_type,
            source_type=source_type, due_date_scope=due_date_scope,
            assigned_user_id=assigned_user_id, location_id=location_id,
            mine_only=mine_only, search_text=search_text,
        )

        # Wiedervorlagen: always full list without type filter
        self.wiedervorlagen = self.task_service.list_tasks(
            task_type=TaskType.WIEDERVORLAGE,
            mine_only=mine_only,
        )

        self.render_table(self.table, self.tasks, show_type=False)
        self.render_table(self.wv_table, self.wiedervorlagen, show_type=True)
        self._update_kpi_chips()

    def _update_kpi_chips(self):
        today = _date.today().isoformat()
        all_open = self.task_service.list_tasks(status=TaskStatus.OFFEN)
        overdue  = [t for t in all_open if t.get("due_date") and t["due_date"] < today]
        today_due = [t for t in all_open if t.get("due_date") == today]
        wv_open  = [t for t in all_open if t.get("task_type") == TaskType.WIEDERVORLAGE]

        self._chip_open.set_value(str(len(all_open)))
        self._chip_over.set_value(str(len(overdue)))
        self._chip_today.set_value(str(len(today_due)))
        self._chip_wv.set_value(str(len(wv_open)))

    def render_table(self, table: TableWidget, tasks: list[dict], show_type: bool = False):
        table.setRowCount(len(tasks))
        today = _date.today().isoformat()

        col_offset = 1 if show_type else 0

        for row_index, task in enumerate(tasks):
            status_badge = _status_badge(task.get("status", ""))
            table.setCellWidget(row_index, 0, status_badge)

            if show_type:
                table.setItem(row_index, 1, QTableWidgetItem(TaskType.get_display(task.get("task_type", ""))))

            table.setItem(row_index, 1 + col_offset, QTableWidgetItem(task["title"]))
            table.setCellWidget(row_index, 2 + col_offset, _priority_badge(task.get("priority", "")))

            due_date = task.get("due_date") or ""
            due_item = QTableWidgetItem(due_date or "-")
            if due_date and task.get("status") != TaskStatus.ERLEDIGT:
                row_color = self._due_color(due_date, today)
                if row_color:
                    col_count = table.columnCount()
                    for col in range(col_count):
                        existing = table.item(row_index, col)
                        if existing:
                            existing.setBackground(QColor(row_color))
            table.setItem(row_index, 3 + col_offset, due_item)

            table.setItem(row_index, 4 + col_offset, QTableWidgetItem(task.get("assigned_user_name") or "-"))
            table.setItem(row_index, 5 + col_offset, QTableWidgetItem(task.get("location_name") or "-"))
            source_text = task.get("source_description") or task.get("source_ref_type") or "-"
            table.setItem(row_index, 6 + col_offset, QTableWidgetItem(source_text))
            table.setItem(row_index, 7 + col_offset, QTableWidgetItem("Ja" if task.get("is_system_task") else "Nein"))
            table.setRowHeight(row_index, 44)

        self.complete_button.setEnabled(False)
        self.delegate_button.setEnabled(False)

    @staticmethod
    def _due_color(due_date: str, today: str) -> str | None:
        try:
            days = (_date.fromisoformat(due_date) - _date.fromisoformat(today)).days
        except Exception:
            return None
        if days < 0:  return "#fde8e8"
        if days == 0: return "#fff3cd"
        if days <= 3: return "#fff9e6"
        return None

    def _current_tasks(self) -> list[dict]:
        if self.tabs.currentIndex() == 1:
            return self.wiedervorlagen
        return self.tasks

    def on_selection_changed(self):
        active_table = self.wv_table if self.tabs.currentIndex() == 1 else self.table
        selected = active_table.selectionModel().selectedRows()
        if not selected:
            self.complete_button.setEnabled(False)
            self.delegate_button.setEnabled(False)
            return
        row  = selected[0].row()
        task = self._current_tasks()[row] if row < len(self._current_tasks()) else None
        if task is None:
            return
        modifiable = not task.get("is_system_task") and task.get("status") != TaskStatus.ERLEDIGT
        self.complete_button.setEnabled(modifiable)
        self.delegate_button.setEnabled(modifiable)

    def on_row_double_clicked(self, row: int, column: int):
        tasks = self._current_tasks()
        if row >= len(tasks):
            return
        task = tasks[row]
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

    def open_new_wiedervorlage_dialog(self):
        dialog = TaskDialog(self.user_service, self.location_service, preset_type=TaskType.WIEDERVORLAGE)
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
        ref_id   = task.get("source_ref_id")

        if ref_type == "claim" and ref_id is not None:
            dialog = ClaimDetailPage(claim_id=ref_id, claim_service=self.claim_service)
            dialog.exec()
            return
        if self.navigate_callback:
            if ref_type == "card":
                self.navigate_callback("cards", filter_context={"search_text": str(ref_id)})
                return
            if ref_type == "document":
                self.navigate_callback("documents", filter_context={"document_id": ref_id})
                return
            if ref_type == "location":
                self.navigate_callback("locations")
                return
        QMessageBox.information(self, "Quelle öffnen", "Die Aufgabe kann nicht direkt geöffnet werden.")

    def delegate_selected_task(self):
        active_table = self.wv_table if self.tabs.currentIndex() == 1 else self.table
        selected = active_table.selectionModel().selectedRows()
        if not selected:
            return
        tasks = self._current_tasks()
        row   = selected[0].row()
        if row >= len(tasks):
            return
        task = tasks[row]
        if task.get("is_system_task"):
            return

        users = self.user_service.get_all_users()
        if not users:
            QMessageBox.information(self, "Delegieren", "Keine Benutzer verfügbar.")
            return

        from PyQt6.QtWidgets import QInputDialog
        names       = [u["full_name"] for u in users]
        current_name = task.get("assigned_user_name") or ""
        start_idx    = names.index(current_name) if current_name in names else 0
        chosen, ok   = QInputDialog.getItem(self, "Aufgabe delegieren", "Neuer Verantwortlicher:", names, start_idx, False)
        if not ok:
            return
        user = next((u for u in users if u["full_name"] == chosen), None)
        if user is None:
            return

        data = {k: task.get(k) for k in [
            "title", "description", "task_type", "status", "priority",
            "due_date", "location_id", "source_type", "source_ref_type",
            "source_ref_id", "source_description",
        ]}
        data["assigned_user_id"] = user["id"]
        try:
            self.task_service.update_task(task_id=task["id"], **data)
            self.refresh_tasks()
        except Exception as exc:
            QMessageBox.warning(self, "Fehler", str(exc))

    def mark_selected_task_done(self):
        active_table = self.wv_table if self.tabs.currentIndex() == 1 else self.table
        selected = active_table.selectionModel().selectedRows()
        if not selected:
            return
        tasks = self._current_tasks()
        row   = selected[0].row()
        if row >= len(tasks):
            return
        task = tasks[row]
        if not task.get("is_system_task") and self.task_service.mark_task_completed(task["id"]):
            self.refresh_tasks()

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

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_tasks()
