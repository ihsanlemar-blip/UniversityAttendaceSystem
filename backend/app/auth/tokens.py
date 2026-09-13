"""Cryptographic token service for JWT access tokens and opaque refresh tokens."""

import hashlib
import secrets
import uuid
from datetime import timedelta
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from backend.app.common.types import utc_now, uuid7
from backend.app.core.config import get_settings
from backend.app.core.exceptions import DomainException


class TokenExpiredException(DomainException):
    """Raised when an access or refresh token has expired."""

    def __init__(self, message: str = "Authentication token has expired.") -> None:
        super().__init__(
            code="TOKEN_EXPIRED",
            message=message,
            status_code=401,
        )


class TokenInvalidException(DomainException):
    """Raised when an authentication token is malformed, tampered, or invalid."""

    def __init__(self, message: str = "Invalid authentication token.") -> None:
        super().__init__(
            code="TOKEN_INVALID",
            message=message,
            status_code=401,
        )


def create_access_token(
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    university_id: uuid.UUID,
    roles: list[str] | None = None,
) -> str:
    """Generate signed, short-lived JWT access token with standardized claims."""
    settings = get_settings()
    now = utc_now()
    expire = now + timedelta(minutes=settings.AUTH_ACCESS_TOKEN_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "sid": str(session_id),
        "university_id": str(university_id),
        "roles": roles or [],
        "typ": "access",
        "jti": str(uuid7()),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": settings.AUTH_ISSUER,
        "aud": settings.AUTH_AUDIENCE,
    }

    token = jwt.encode(
        payload,
        settings.AUTH_SIGNING_KEY,
        algorithm=settings.AUTH_ALGORITHM,
    )
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate and decode JWT access token.

    Validates signature, algorithm, issuer, audience, expiration, not-before,
    and token type.
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.AUTH_SIGNING_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
            issuer=settings.AUTH_ISSUER,
            audience=settings.AUTH_AUDIENCE,
            options={
                "require": ["sub", "sid", "university_id", "exp", "iat", "nbf", "iss", "aud"],
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
    except ExpiredSignatureError as e:
        raise TokenExpiredException("Access token has expired.") from e
    except InvalidTokenError as e:
        raise TokenInvalidException("Malformed or invalid access token.") from e

    if payload.get("typ") != "access":
        raise TokenInvalidException("Invalid token type. Expected access token.")

    return payload


def generate_refresh_token() -> tuple[str, str]:
    """Generate high-entropy cryptographically secure refresh token.

    Returns:
        tuple[str, str]: (raw_token, sha256_token_hash)
    """
    # 48 bytes URL-safe = 64 random characters with 384 bits of entropy
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(raw_token)
    return raw_token, token_hash


def hash_refresh_token(raw_token: str) -> str:
    """Compute SHA-256 digest of raw refresh token for safe storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
