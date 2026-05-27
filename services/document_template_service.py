import re
from core.session import Session
from database.repositories.document_template_repository import DocumentTemplateRepository


TEMPLATE_TYPES = ["BRIEF", "BESCHEID", "FORMULAR", "INFORMATION"]

PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")

DEFAULT_PLACEHOLDERS = {
    "VORNAME":        "Vorname der Person",
    "NACHNAME":       "Nachname der Person",
    "ADRESSE":        "Adresse der Person",
    "PLZ":            "Postleitzahl",
    "ORT":            "Ort/Stadt",
    "AKTENZEICHEN":   "Aktenzeichen des Antrags",
    "DATUM":          "Aktuelles Datum",
    "STANDORT":       "Name des Standorts",
    "MITARBEITER":    "Name des Mitarbeiters",
}


class DocumentTemplateService:
    def __init__(self, repo: DocumentTemplateRepository | None = None):
        self.repo = repo or DocumentTemplateRepository()

    def list_templates(self, include_inactive: bool = False) -> list[dict]:
        return self.repo.list_templates(include_inactive=include_inactive)

    def get_template(self, template_id: int) -> dict | None:
        return self.repo.get_by_id(template_id)

    def create_template(self, data: dict) -> int:
        if not data.get("name", "").strip():
            raise ValueError("Vorlagenname ist Pflichtfeld.")
        data["created_by"] = Session.get_user_id()
        return self.repo.create(data)

    def update_template(self, template_id: int, data: dict) -> None:
        if not data.get("name", "").strip():
            raise ValueError("Vorlagenname ist Pflichtfeld.")
        self.repo.update(template_id, data)

    def delete_template(self, template_id: int) -> None:
        self.repo.delete(template_id)

    def get_placeholders(self) -> dict[str, str]:
        return DEFAULT_PLACEHOLDERS.copy()

    def render(self, template_id: int, context: dict) -> str:
        """Replace {{PLACEHOLDER}} in body_text with values from context."""
        tpl = self.repo.get_by_id(template_id)
        if not tpl:
            raise ValueError("Vorlage nicht gefunden.")
        body = tpl["body_text"] or ""

        def replace(m: re.Match) -> str:
            key = m.group(1).upper()
            return str(context.get(key, f"{{{{{key}}}}}"))

        return PLACEHOLDER_RE.sub(replace, body)

    def extract_placeholders(self, body_text: str) -> list[str]:
        return list({m.upper() for m in PLACEHOLDER_RE.findall(body_text)})
