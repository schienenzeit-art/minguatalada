from app.ports import UserRepositoryPort
from database.repositories.user_repository import UserRepository
from services.password_service import PasswordService
from datetime import datetime, timedelta

# Security configuration
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class AuthService:
    def __init__(self, user_repository: UserRepositoryPort | None = None) -> None:
        self.user_repository = user_repository or UserRepository()

    def login(self, username: str, password: str) -> dict:
        username = username.strip()
        password = password.strip()

        if not username or not password:
            return {
                "success": False,
                "message": "Benutzername und Passwort sind erforderlich.",
                "user": None,
            }

        user = self.user_repository.get_by_username(username)

        if user is None:
            return {
                "success": False,
                "message": "Benutzer nicht gefunden.",
                "user": None,
            }

        # check account active status
        if not user["is_active"]:
            return {
                "success": False,
                "message": "Benutzer ist deaktiviert.",
                "user": None,
            }

        # Rollen ohne Systemzugang können sich nie einloggen
        from core.constants import NON_LOGIN_ROLES
        if user.get("role_name", "") in NON_LOGIN_ROLES:
            return {
                "success": False,
                "message": "Dieser Eintrag ist für keinen Systemzugang vorgesehen.",
                "user": None,
            }

        # check account lockout
        locked_until = user.get("locked_until")
        if locked_until:
            try:
                locked_dt = datetime.fromisoformat(locked_until)
                if locked_dt > datetime.utcnow():
                    return {
                        "success": False,
                        "message": f"Account gesperrt bis {locked_until}.",
                        "user": None,
                    }
            except Exception:
                # ignore parse errors and continue
                pass

        if not PasswordService.verify_password(password, user["password_hash"]):
            # increment failed attempts and possibly lock account
            try:
                self.user_repository.increment_failed_attempts(user["id"])
                updated = self.user_repository.get_by_id(user["id"])
                if updated and updated.get("failed_attempts", 0) >= MAX_FAILED_ATTEMPTS:
                    lock_until = (datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
                    self.user_repository.set_locked_until(user["id"], lock_until)
                # refresh user
            except Exception:
                pass
            return {
                "success": False,
                "message": "Passwort ist falsch.",
                "user": None,
            }

        # successful login: reset failed attempts and locked_until
        try:
            self.user_repository.reset_failed_attempts(user["id"])
        except Exception:
            pass

        return {
            "success": True,
            "message": "Login erfolgreich.",
            "user": user,
            "must_change_password": bool(user.get("must_change_password", False)),
        }