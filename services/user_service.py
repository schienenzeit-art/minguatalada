from typing import Any, Dict, List, Optional

from app.ports import UserRepositoryPort
from database.repositories.user_repository import UserRepository
from services.password_service import PasswordService


class UserService:
    def __init__(self, user_repository: UserRepositoryPort | None = None):
        self.user_repository = user_repository or UserRepository()

    def get_all_users(self) -> List[dict]:
        return self.user_repository.get_all()

    def get_roles(self) -> List[dict]:
        return self.user_repository.get_roles()

    def get_locations(self) -> List[dict]:
        return self.user_repository.get_locations()

    def get_users_by_location(self, location_id: Optional[int] = None) -> List[dict]:
        return self.user_repository.get_users_by_location_id(location_id)

    def get_user_counts_by_role(self) -> List[dict]:
        return self.user_repository.get_user_counts_by_role()

    def get_user_counts_by_location(self) -> List[dict]:
        return self.user_repository.get_user_counts_by_location()

    def create_user(
        self,
        full_name: str,
        username: str,
        password: str,
        role_id: int,
        location_id: Optional[int],
        is_active: bool = True,
    ) -> Dict[str, Any]:
        full_name = full_name.strip()
        username = username.strip()
        password = password.strip()

        if not full_name or not username or not password:
            return {
                "success": False,
                "message": "Name, Benutzername und Passwort sind erforderlich.",
            }

        if self.user_repository.get_by_username(username) is not None:
            return {
                "success": False,
                "message": "Benutzername existiert bereits.",
            }

        password_hash = PasswordService.hash_password(password)
        self.user_repository.create(
            full_name,
            username,
            password_hash,
            role_id,
            location_id,
            is_active,
        )

        return {
            "success": True,
            "message": "Benutzer wurde angelegt.",
        }

    def set_user_active(self, user_id: int, is_active: bool) -> None:
        self.user_repository.set_active(user_id, is_active)

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, object]]:
        return self.user_repository.get_by_id(user_id)

    def update_user(
        self,
        user_id: int,
        full_name: str,
        username: str,
        role_id: int,
        location_id: Optional[int],
        is_active: bool,
        password: Optional[str] = None,
    ) -> Dict[str, object]:
        existing = self.user_repository.get_by_id(user_id)
        if existing is None:
            return {"success": False, "message": "Benutzer nicht gefunden."}

        if not full_name.strip() or not username.strip() or role_id is None:
            return {"success": False, "message": "Name, Benutzername und Rolle sind erforderlich."}

        same_user = self.user_repository.get_by_username(username.strip())
        if same_user is not None and same_user["id"] != user_id:
            return {"success": False, "message": "Benutzername existiert bereits."}

        password_hash = None
        if password:
            password_hash = PasswordService.hash_password(password.strip())

        updated = self.user_repository.update_user(
            user_id=user_id,
            full_name=full_name,
            username=username,
            role_id=role_id,
            location_id=location_id,
            is_active=is_active,
            password_hash=password_hash,
        )

        return {
            "success": updated,
            "message": "Benutzer wurde aktualisiert." if updated else "Benutzer konnte nicht aktualisiert werden.",
        }
