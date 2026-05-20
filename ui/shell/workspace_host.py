from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget


class WorkspaceHost(QWidget):
    def __init__(self):
        super().__init__()
        self.page_widgets: dict[str, QWidget] = {}
        self.stack = QStackedWidget()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stack)

        self.setLayout(layout)

    def register_page(self, key: str, widget: QWidget) -> None:
        self.page_widgets[key] = widget
        self.stack.addWidget(widget)

    def set_current_page(self, key: str) -> None:
        page = self.page_widgets.get(key)
        if page:
            self.stack.setCurrentWidget(page)

    def current_page(self) -> str | None:
        for key, widget in self.page_widgets.items():
            if self.stack.currentWidget() is widget:
                return key
        return None
