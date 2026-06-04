from typing import Any, Dict, Optional

UserType = Dict[str, Any]


class Session:
    _current_user: Optional[UserType] = None

    @classmethod
    def set_user(cls, user: UserType) -> None:
        cls._current_user = user

    @classmethod
    def get_user(cls) -> Optional[UserType]:
        return cls._current_user

    @classmethod
    def require_user(cls) -> UserType:
        """Gibt den aktuellen User zurück oder wirft RuntimeError wenn keine Session aktiv ist."""
        user = cls._current_user
        if user is None:
            raise RuntimeError("Keine aktive Session. Bitte zuerst einloggen.")
        return user

    @classmethod
    def clear(cls) -> None:
        cls._current_user = None

    @classmethod
    def is_authenticated(cls) -> bool:
        return cls._current_user is not None

    @classmethod
    def get_user_id(cls) -> Optional[int]:
        user = cls.get_user()
        return user.get("id") if user else None

    @classmethod
    def get_full_name(cls) -> Optional[str]:
        user = cls.get_user()
        return user.get("full_name") if user else None

    @classmethod
    def get_role_name(cls) -> Optional[str]:
        user = cls.get_user()
        return user.get("role_name") if user else None

    @classmethod
    def has_role(cls, role_name: str) -> bool:
        current_role = cls.get_role_name()
        return current_role == role_name

    @classmethod
    def is_admin(cls) -> bool:
        return cls.has_role("Admin")

    @classmethod
    def is_standortleitung(cls) -> bool:
        return cls.has_role("Standortleitung")

    @classmethod
    def is_mitarbeiter(cls) -> bool:
        return cls.has_role("Mitarbeiter")

    @classmethod
    def get_location_id(cls) -> Optional[int]:
        user = cls.get_user()
        return user.get("location_id") if user else None

    @classmethod
    def get_location_name(cls) -> Optional[str]:
        user = cls.get_user()
        return user.get("location_name") if user else None
