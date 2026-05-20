from dataclasses import dataclass
from typing import Callable, Dict, Optional

from PyQt6.QtWidgets import QWidget
from ui.shell.workspace_host import WorkspaceHost


@dataclass
class Route:
    key: str
    widget: QWidget
    title: str
    parent_app: str


class NavigationController:
    def __init__(self, workspace_host: WorkspaceHost, page_changed_callback: Optional[Callable[[str], None]] = None):
        self.workspace_host = workspace_host
        self.page_changed_callback = page_changed_callback
        self.routes: Dict[str, Route] = {}
        self.current_page: Optional[str] = None

    def register_route(self, key: str, widget: QWidget, title: str, parent_app: str | None = None) -> None:
        route = Route(key=key, widget=widget, title=title, parent_app=parent_app or key)
        self.routes[key] = route
        self.workspace_host.register_page(key, widget)

    def navigate(self, page: str, filter_context: dict | None = None) -> None:
        route = self.routes.get(page)
        if route is None:
            return

        if filter_context and hasattr(route.widget, "apply_filters"):
            route.widget.apply_filters(**filter_context)

        self.current_page = page
        self.workspace_host.set_current_page(page)

        if self.page_changed_callback:
            self.page_changed_callback(page)

    def get_page_title(self, page: str) -> str:
        route = self.routes.get(page)
        return route.title if route else "Anspruchssystem"

    def get_parent_app(self, page: str) -> str:
        route = self.routes.get(page)
        return route.parent_app if route else page
