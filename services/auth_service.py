from app.ports import UserRepositoryPort
from database.repositories.user_repository import UserRepository
from services.password_service import PasswordService
from datetime import datetime, timedelta, UTC
import logging

# Security configuration
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, user_repository: UserRepositoryPort | None = None) -> None:
        self.user_repository = user_repository or UserRepository()

    def login(self, username: str, password: str) -> dict:
        username = username.strip()
        password = password.strip()

        if not username or not password:
            logger.warning("LOGIN_ATTEMPT: leere Felder (kein Benutzername/Passwort)")
            return {
                "success": False,
                "message": "Benutzername und Passwort sind erforderlich.",
                "user": None,
            }

        user = self.user_repository.get_by_username(username)

        if user is None:
            logger.warning("LOGIN_FAILED: Benutzer '%s' nicht gefunden.", username)
            self._audit("LOGIN_FAILED", None, f"Unbekannter Benutzername: {username}")
            return {
                "success": False,
                "message": "Benutzer nicht gefunden.",
                "user": None,
            }

        # check account active status
        if not user["is_active"]:
            logger.warning("LOGIN_FAILED: Benutzer '%s' ist deaktiviert.", username)
            self._audit("LOGIN_FAILED", user["id"], f"Deaktivierter Account: {username}")
            return {
                "success": False,
                "message": "Benutzer ist deaktiviert. Bitte wenden Sie sich an einen Administrator.",
                "user": None,
            }

        # Rollen ohne Systemzugang können sich nie einloggen
        from core.constants import NON_LOGIN_ROLES
        if user.get("role_name", "") in NON_LOGIN_ROLES:
            logger.warning("LOGIN_FAILED: Benutzer '%s' hat keine Login-Berechtigung (Rolle: %s).", username, user.get("role_name"))
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
                if locked_dt > datetime.now(UTC):
                    logger.warning("LOGIN_FAILED: Account '%s' gesperrt bis %s.", username, locked_until)
                    self._audit("ACCOUNT_LOCKED", user["id"], f"Login abgelehnt — gesperrt bis {locked_until}")
                    return {
                        "success": False,
                        "message": "Account ist gesperrt. Bitte wenden Sie sich an einen Administrator.",
                        "user": None,
                    }
            except Exception:
                pass

        if not PasswordService.verify_password(password, user["password_hash"]):
            try:
                self.user_repository.increment_failed_attempts(user["id"])
                updated = self.user_repository.get_by_id(user["id"])
                attempts = updated.get("failed_attempts", 0) if updated else 0
                if attempts >= MAX_FAILED_ATTEMPTS:
                    lock_until = (datetime.now(UTC) + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
                    self.user_repository.set_locked_until(user["id"], lock_until)
                    logger.warning("ACCOUNT_LOCKED: '%s' nach %d Fehlversuchen gesperrt.", username, attempts)
                    self._audit("ACCOUNT_LOCKED", user["id"], f"Account nach {attempts} Fehlversuchen für {LOCKOUT_MINUTES} Min. gesperrt.")
            except Exception:
                pass
            logger.warning("LOGIN_FAILED: Falsches Passwort für '%s'.", username)
            self._audit("LOGIN_FAILED", user["id"], f"Falsches Passwort für: {username}")
            return {
                "success": False,
                "message": "Passwort ist falsch.",
                "user": None,
            }

        # successful login
        try:
            self.user_repository.reset_failed_attempts(user["id"])
        except Exception:
            pass

        logger.info("LOGIN_SUCCESS: Benutzer '%s' angemeldet (Rolle: %s).", username, user.get("role_name"))
        self._audit("LOGIN_SUCCESS", user["id"], f"Anmeldung: {username} (Rolle: {user.get('role_name')})")

        return {
            "success": True,
            "message": "Login erfolgreich.",
            "user": user,
            "must_change_password": bool(user.get("must_change_password", False)),
        }

    def _audit(self, action: str, user_id: int | None, details: str) -> None:
        """Schreibt Login-Ereignisse direkt in audit_logs (ohne Session-Kontext)."""
        try:
            from database.repositories.audit_repository import AuditRepository
            AuditRepository().log(user_id, action, "auth", None, details)
        except Exception:
            pass