from dataclasses import dataclass
from typing import ClassVar, List

from core.session import Session


@dataclass(frozen=True)
class AppMetadata:
    id: str
    title: str
    description: str
    page_key: str
    admin_only: bool = False
    visible: bool = True


class AppRegistry:
    APPS: ClassVar[List[AppMetadata]] = [
        AppMetadata(
            id="anspruchspruefung",
            title="Anspruchsprüfung",
            description="Prüfung, Berechnung und Kartenableitung",
            page_key="anspruchspruefung",
        ),
        AppMetadata(
            id="aufgaben",
            title="Actionboard",
            description="Operative Aufgaben und Fristensteuerung",
            page_key="tasks",
        ),
        AppMetadata(
            id="dokumente",
            title="Dokumente",
            description="Belege, PDFs und Archivzugang",
            page_key="documents",
        ),
        AppMetadata(
            id="reporting",
            title="Reporting",
            description="Kennzahlen, Auswertungen und Berichte",
            page_key="reports",
        ),
        AppMetadata(
            id="administration",
            title="Administration",
            description="Benutzer, Standorte und Systemeinstellungen",
            page_key="administration",
            admin_only=True,
        ),
    ]

    @classmethod
    def get_visible_apps(cls) -> List[AppMetadata]:
        return [
            app
            for app in cls.APPS
            if app.visible and (not app.admin_only or Session.is_admin())
        ]

    @classmethod
    def get_app(cls, page_key: str) -> AppMetadata | None:
        return next((app for app in cls.APPS if app.page_key == page_key), None)
