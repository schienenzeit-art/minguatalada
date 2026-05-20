from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout

from app.app_registry import AppRegistry
from ui.components.app_card import AppCard


class AppLauncherSection(QWidget):
    def __init__(self, navigate_callback=None):
        super().__init__()
        self.navigate_callback = navigate_callback
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("appLauncherSection")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        section_title = QLabel("Applikationen starten")
        section_title.setObjectName("dashboardSectionTitle")
        layout.addWidget(section_title)

        apps_layout = QHBoxLayout()
        apps_layout.setSpacing(16)

        for app in AppRegistry.get_visible_apps():
            card = AppCard(title=app.title, subtitle=app.description)
            card.clicked.connect(lambda _, page_key=app.page_key: self.on_app_clicked(page_key))
            apps_layout.addWidget(card)

        layout.addLayout(apps_layout)
        self.setLayout(layout)

    def on_app_clicked(self, page_key: str):
        if self.navigate_callback:
            self.navigate_callback(page_key)
