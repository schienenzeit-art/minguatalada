from typing import List, Dict, Optional

from database.repositories.location_repository import LocationRepository


class LocationService:
    def __init__(self):
        self.location_repository = LocationRepository()

    def list_locations(self, include_inactive: bool = False) -> List[Dict[str, object]]:
        return self.location_repository.list_locations(include_inactive=include_inactive)

    def list_active_locations(self) -> List[Dict[str, object]]:
        return self.location_repository.list_locations(include_inactive=False)

    def create_location(self, name: str) -> Dict[str, object]:
        location_id = self.location_repository.create_location(name)
        return {"id": location_id, "name": name.strip(), "is_active": True}

    def update_location(self, location_id: int, name: str) -> bool:
        return self.location_repository.update_location(location_id, name)

    def set_location_active(self, location_id: int, is_active: bool) -> bool:
        return self.location_repository.set_active(location_id, is_active)

    def get_location_by_id(self, location_id: int) -> Optional[Dict[str, object]]:
        return self.location_repository.get_location_by_id(location_id)
