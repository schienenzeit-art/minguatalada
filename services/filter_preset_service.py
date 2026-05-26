from __future__ import annotations

from core.session import Session
from database.repositories.filter_preset_repository import FilterPresetRepository


class FilterPresetService:
    def __init__(self, repository: FilterPresetRepository | None = None):
        self.repo = repository or FilterPresetRepository()

    def save_preset(self, name: str, filter_dict: dict) -> int | None:
        return self.repo.create_preset(Session.get_user_id(), name, filter_dict)

    def get_presets(self) -> list[dict]:
        return self.repo.get_presets(Session.get_user_id())

    def delete_preset(self, preset_id: int) -> bool:
        return self.repo.delete_preset(preset_id)
