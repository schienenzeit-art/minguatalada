from typing import Any, Dict, List, Optional

from app.ports import UserRepositoryPort
from database.repositories.user_repository import UserRepository
from services.password_service import PasswordService
from services.auth_service import MAX_FAILED_ATTEMPTS
from datetime import datetime


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
        # audit
        try:
            created = self.user_repository.get_by_username(username)
            if created:
                self.user_repository.log_audit(created.get("id"), "create_user", "user", created.get("id"), f"User {username} created")
        except Exception:
            pass

        return {
            "success": True,
            "message": "Benutzer wurde angelegt.",
        }

    def set_user_active(self, user_id: int, is_active: bool) -> None:
        self.user_repository.set_active(user_id, is_active)
        try:
            self.user_repository.log_audit(None, "set_active", "user", user_id, f"set_active={is_active}")
        except Exception:
            pass

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

        try:
            if updated:
                self.user_repository.log_audit(None, "update_user", "user", user_id, f"updated user {username}")
        except Exception:
            pass

        return {
            "success": updated,
            "message": "Benutzer wurde aktualisiert." if updated else "Benutzer konnte nicht aktualisiert werden.",
        }

        # audit handled by caller if needed

    def change_password(self, user_id: int, current_password: str, new_password: str) -> Dict[str, object]:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            return {"success": False, "message": "Benutzer nicht gefunden."}

        if not PasswordService.verify_password(current_password, user["password_hash"]):
            return {"success": False, "message": "Aktuelles Passwort ist falsch."}

        if len(new_password) < 10:
            return {"success": False, "message": "Neues Passwort muss mindestens 10 Zeichen lang sein."}

        password_hash = PasswordService.hash_password(new_password)
        updated = self.user_repository.update_user(
            user_id=user_id,
            full_name=user["full_name"],
            username=user["username"],
            role_id=user.get("role_id", None) or 1,
            location_id=user.get("location_id"),
            is_active=True,
            password_hash=password_hash,
        )

        try:
            if updated:
                self.user_repository.log_audit(user_id, "change_password", "user", user_id, "user changed own password")
        except Exception:
            pass

        return {"success": updated, "message": "Passwort geändert." if updated else "Passwort konnte nicht geändert werden."}

    def admin_reset_password(self, admin_user_id: int, target_user_id: int, new_password: str) -> Dict[str, object]:
        # minimal check: admin_user_id must belong to Admin role
        admin = self.user_repository.get_by_id(admin_user_id)
        if admin is None or admin.get("role_name") != "Admin":
            return {"success": False, "message": "Keine Berechtigung."}

        if len(new_password) < 10:
            return {"success": False, "message": "Neues Passwort muss mindestens 10 Zeichen lang sein."}

        password_hash = PasswordService.hash_password(new_password)
        target = self.user_repository.get_by_id(target_user_id)
        if target is None:
            return {"success": False, "message": "Zielbenutzer nicht gefunden."}

        updated = self.user_repository.update_user(
            user_id=target_user_id,
            full_name=target["full_name"],
            username=target["username"],
            role_id=target.get("role_id", 1),
            location_id=target.get("location_id"),
            is_active=bool(target.get("is_active", True)),
            password_hash=password_hash,
        )

        try:
            if updated:
                self.user_repository.log_audit(admin_user_id, "admin_reset_password", "user", target_user_id, "admin reset password")
        except Exception:
            pass

        return {"success": updated, "message": "Passwort zurückgesetzt." if updated else "Passwort konnte nicht zurückgesetzt werden."}
