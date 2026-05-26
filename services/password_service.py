import bcrypt
import secrets
import string


class PasswordService:
    """Password hashing and verification using bcrypt.

    This replaces PBKDF2-based hashing with bcrypt, suitable for password storage.
    """
    BCRYPT_ROUNDS = 12

    @classmethod
    def hash_password(cls, password: str) -> str:
        pw = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=cls.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(pw, salt)
        return hashed.decode("utf-8")

    @classmethod
    def verify_password(cls, password: str, stored_hash: str) -> bool:
        if not stored_hash:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        except Exception:
            return False

    @classmethod
    def generate_random_password(cls, length: int = 16) -> str:
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
