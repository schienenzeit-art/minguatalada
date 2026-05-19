from typing import List, Dict, Optional

from database.repositories.role_repository import RoleRepository


class RoleService:
    def __init__(self):
        self.role_repository = RoleRepository()

    def list_roles(self, include_inactive: bool = False) -> List[Dict[str, object]]:
        return self.role_repository.list_roles(include_inactive=include_inactive)

    def create_role(self, name: str) -> Dict[str, object]:
        role_id = self.role_repository.create_role(name)
        return {"id": role_id, "name": name.strip(), "is_active": True}

    def update_role(self, role_id: int, name: str) -> bool:
        return self.role_repository.update_role(role_id, name)

    def set_role_active(self, role_id: int, is_active: bool) -> bool:
        return self.role_repository.set_active(role_id, is_active)

    def get_role_by_id(self, role_id: int) -> Optional[Dict[str, object]]:
        return self.role_repository.get_role_by_id(role_id)
