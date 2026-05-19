from app.ports import UserRepositoryPort
from database.repositories.user_repository import UserRepository
from services.password_service import PasswordService


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

        if not user["is_active"]:
            return {
                "success": False,
                "message": "Benutzer ist deaktiviert.",
                "user": None,
            }

        if not PasswordService.verify_password(password, user["password_hash"]):
            return {
                "success": False,
                "message": "Passwort ist falsch.",
                "user": None,
            }

        return {
            "success": True,
            "message": "Login erfolgreich.",
            "user": user,
        }


print("AUTH SERVICE END")