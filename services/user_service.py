from typing import Any, Dict, List, Optional

from app.ports import UserRepositoryPort
from core.constants import NON_LOGIN_ROLES
from database.repositories.user_repository import UserRepository
from services.password_service import PasswordService

# Benutzer die niemals deaktiviert oder gelöscht werden dürfen
_PROTECTED_USERNAMES = frozenset({"admin"})

# Rollen mit Zugriff auf Benutzerverwaltung
USERMGMT_ALLOWED_ROLES = frozenset({"Admin", "Supervisor", "Standortleitung"})


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

    def _get_role_name(self, role_id: int) -> str:
        """Rollenname anhand der ID nachschlagen."""
        roles = self.user_repository.get_roles()
        role = next((r for r in roles if r["id"] == role_id), None)
        return role["name"] if role else ""

    def create_user(
        self,
        full_name: str,
        username: str,
        password: str,
        role_id: int,
        location_id: Optional[int],
        is_active: bool = True,
        must_change_password: bool = True,
    ) -> Dict[str, Any]:
        # Rollenprüfung: Nur Admin/Supervisor/Standortleitung dürfen Benutzer anlegen
        from core.session import Session as _Session
        caller_role = (_Session.get_user() or {}).get("role_name", "")
        if caller_role and caller_role not in USERMGMT_ALLOWED_ROLES:
            return {
                "success": False,
                "message": "Keine Berechtigung. Nur Admin und Supervisor dürfen Benutzer anlegen.",
            }

        full_name = full_name.strip()
        username = username.strip()

        # Rollentyp bestimmen: Freiwillige benötigen kein Passwort
        target_role_name = self._get_role_name(role_id)
        is_volunteer = target_role_name in NON_LOGIN_ROLES

        if is_volunteer:
            # Zufälliger Platzhalter – niemand kennt dieses Passwort, Login wird
            # zusätzlich durch die Rollenprüfung im AuthService verhindert.
            import secrets
            password = secrets.token_hex(32)
            must_change_password = False
        else:
            password = password.strip()
            if not password:
                return {
                    "success": False,
                    "message": "Passwort ist für diesen Benutzertyp erforderlich.",
                }

        if not full_name or not username:
            return {
                "success": False,
                "message": "Name und Benutzername sind erforderlich.",
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
        try:
            created = self.user_repository.get_by_username(username)
            if created:
                if must_change_password:
                    self.user_repository.set_must_change_password(created["id"], True)
                action = "create_volunteer" if is_volunteer else "create_user"
                self.user_repository.log_audit(
                    created.get("id"), action, "user", created.get("id"),
                    f"{'Freiwillige/r' if is_volunteer else 'Benutzer'} {username} angelegt"
                )
        except Exception:
            pass

        return {
            "success": True,
            "message": "Eintrag wurde angelegt.",
            "is_volunteer": is_volunteer,
        }

    def set_user_active(self, user_id: int, is_active: bool) -> Dict[str, Any]:
        target = self.user_repository.get_by_id(user_id)
        if target and target.get("username") in _PROTECTED_USERNAMES and not is_active:
            return {"success": False, "message": "Der Systemadministrator kann nicht deaktiviert werden."}
        self.user_repository.set_active(user_id, is_active)
        try:
            self.user_repository.log_audit(None, "set_active", "user", user_id, f"set_active={is_active}")
        except Exception:
            pass
        return {"success": True, "message": "Status aktualisiert."}

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, object]]:
        return self.user_repository.get_by_id(user_id)

    def delete_user(self, user_id: int) -> Dict[str, Any]:
        """Löscht einen Benutzer. Systemadministrator und Mitarbeiter/Freiwillige sind geschützt."""
        target = self.user_repository.get_by_id(user_id)
        if target is None:
            return {"success": False, "message": "Benutzer nicht gefunden."}
        if target.get("username") in _PROTECTED_USERNAMES:
            return {"success": False, "message": "Der Systemadministrator kann nicht gelöscht werden."}
        role_name = target.get("role_name", "")
        if role_name in ("Mitarbeiter",):
            return {"success": False, "message": "Mitarbeiter und Freiwillige dürfen nicht gelöscht werden. Status kann auf 'Inaktiv' gesetzt werden."}
        return {"success": False, "message": "Löschen ist in dieser Anwendung nicht vorgesehen. Benutzer bitte deaktivieren."}

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
        if existing.get("username") in _PROTECTED_USERNAMES and not is_active:
            return {"success": False, "message": "Der Systemadministrator kann nicht deaktiviert werden."}

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

    def set_must_change_password(self, user_id: int, flag: bool) -> None:
        self.user_repository.set_must_change_password(user_id, flag)
        try:
            self.user_repository.log_audit(None, "set_must_change_password", "user", user_id, f"flag={flag}")
        except Exception:
            pass

    def manual_lock_user(self, user_id: int, locked_until_iso: str | None) -> None:
        self.user_repository.set_locked_until(user_id, locked_until_iso)
        try:
            self.user_repository.log_audit(None, "manual_lock_user", "user", user_id, f"locked_until={locked_until_iso}")
        except Exception:
            pass

    def admin_reset_password(self, admin_user_id: int, target_user_id: int, new_password: str) -> Dict[str, object]:
        # minimal check: admin_user_id must belong to Admin role
        admin = self.user_repository.get_by_id(admin_user_id)
        if admin is None or admin.get("role_name") != "Admin":
            return {"success": False, "message": "Keine Berechtigung."}

        # Freiwillige haben keinen Systemzugang → kein Passwort-Reset
        target_check = self.user_repository.get_by_id(target_user_id)
        if target_check and target_check.get("role_name", "") in NON_LOGIN_ROLES:
            return {"success": False, "message": "Freiwillige haben keinen Systemzugang. Passwort-Reset nicht möglich."}

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
