"""Password security service implementing Argon2id hashing and verification."""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from backend.app.core.config import get_settings
from backend.app.core.exceptions import ValidationException

# Initialize password hash engine with Argon2id
password_hash_engine = PasswordHash((Argon2Hasher(),))


def validate_password_policy(password: str) -> None:
    """Validate password against institutional security policies.

    Policy:
    1. Rejects empty passwords.
    2. Enforces minimum length (configurable, default 8).
    3. Enforces reasonable maximum length (128) to prevent ReDoS / CPU exhaustion.
    4. Preserves full Unicode safely without trimming or silent alteration.
    """
    settings = get_settings()

    if not password:
        raise ValidationException("Password cannot be empty.", details={"field": "password"})

    if len(password) < settings.AUTH_PASSWORD_MIN_LENGTH:
        raise ValidationException(
            f"Password must be at least {settings.AUTH_PASSWORD_MIN_LENGTH} characters long.",
            details={"min_length": settings.AUTH_PASSWORD_MIN_LENGTH},
        )

    if len(password) > settings.AUTH_PASSWORD_MAX_LENGTH:
        raise ValidationException(
            f"Password cannot exceed {settings.AUTH_PASSWORD_MAX_LENGTH} characters.",
            details={"max_length": settings.AUTH_PASSWORD_MAX_LENGTH},
        )


def hash_password(password: str) -> str:
    """Hash plaintext password using Argon2id.

    Validates password policy prior to hashing.
    """
    validate_password_policy(password)
    return password_hash_engine.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    """Verify plain password against stored hash.

    Returns:
        tuple[bool, str | None]: (is_valid, updated_hash_if_rehash_needed)
    """
    if not plain_password or not hashed_password:
        return False, None

    try:
        is_valid, updated_hash = password_hash_engine.verify_and_update(
            plain_password, hashed_password
        )
        return is_valid, updated_hash
    except Exception:
        return False, None
