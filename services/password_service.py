import hashlib
import secrets


class PasswordService:
    ALGORITHM = "pbkdf2_sha256"
    ITERATIONS = 150000
    SALT_LENGTH = 16

    @classmethod
    def hash_password(cls, password: str) -> str:
        salt = secrets.token_hex(cls.SALT_LENGTH)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            cls.ITERATIONS,
        )
        return f"{cls.ALGORITHM}${cls.ITERATIONS}${salt}${digest.hex()}"

    @classmethod
    def verify_password(cls, password: str, stored_hash: str) -> bool:
        if not stored_hash:
            return False

        parts = stored_hash.split("$")
        if len(parts) != 4:
            return password == stored_hash

        algorithm, iterations, salt, digest = parts
        if algorithm != cls.ALGORITHM:
            return False

        new_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return secrets.compare_digest(new_digest, digest)
