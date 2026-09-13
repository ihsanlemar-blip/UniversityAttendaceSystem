"""Unit tests for cryptographic token creation, claims validation, and expiration."""

from datetime import timedelta

import jwt
import pytest

from backend.app.auth.tokens import (
    TokenExpiredException,
    TokenInvalidException,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from backend.app.common.types import utc_now, uuid7
from backend.app.core.config import get_settings


def test_access_token_creation_and_decoding() -> None:
    """Verify standard access token issuance and accurate claims decoding."""
    user_id = uuid7()
    session_id = uuid7()
    uni_id = uuid7()
    roles = ["STUDENT", "AUDITOR"]

    token = create_access_token(
        user_id=user_id,
        session_id=session_id,
        university_id=uni_id,
        roles=roles,
    )

    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["sid"] == str(session_id)
    assert payload["university_id"] == str(uni_id)
    assert payload["roles"] == roles
    assert payload["typ"] == "access"
    assert "jti" in payload
    assert "iat" in payload
    assert "nbf" in payload
    assert "exp" in payload
    assert payload["iss"] == "university-attendance-api"
    assert payload["aud"] == "university-attendance-client"


def test_access_token_expiration_rejection() -> None:
    """Verify expired token raises TokenExpiredException."""
    settings = get_settings()
    user_id = uuid7()
    session_id = uuid7()
    uni_id = uuid7()
    now = utc_now()

    # Create expired payload directly
    expired_payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "university_id": str(uni_id),
        "roles": ["STUDENT"],
        "typ": "access",
        "jti": str(uuid7()),
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "nbf": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
        "iss": settings.AUTH_ISSUER,
        "aud": settings.AUTH_AUDIENCE,
    }
    expired_token = jwt.encode(
        expired_payload,
        settings.AUTH_SIGNING_KEY,
        algorithm=settings.AUTH_ALGORITHM,
    )

    with pytest.raises(TokenExpiredException, match="expired"):
        decode_access_token(expired_token)


def test_access_token_tampered_signature_rejection() -> None:
    """Verify altered token payload or signature is rejected."""
    user_id = uuid7()
    session_id = uuid7()
    uni_id = uuid7()

    token = create_access_token(
        user_id=user_id,
        session_id=session_id,
        university_id=uni_id,
        roles=["LECTURER"],
    )

    # Tamper with token string
    tampered_token = token[:-5] + ("AAAAA" if token[-5:] != "AAAAA" else "BBBBB")

    with pytest.raises(TokenInvalidException):
        decode_access_token(tampered_token)


def test_access_token_wrong_issuer_rejection() -> None:
    """Verify token signed with unexpected issuer is rejected."""
    settings = get_settings()
    user_id = uuid7()
    now = utc_now()

    payload = {
        "sub": str(user_id),
        "sid": str(uuid7()),
        "university_id": str(uuid7()),
        "roles": ["STUDENT"],
        "typ": "access",
        "jti": str(uuid7()),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "iss": "rogue-issuer",
        "aud": settings.AUTH_AUDIENCE,
    }
    token = jwt.encode(payload, settings.AUTH_SIGNING_KEY, algorithm=settings.AUTH_ALGORITHM)

    with pytest.raises(TokenInvalidException):
        decode_access_token(token)


def test_access_token_wrong_audience_rejection() -> None:
    """Verify token intended for different audience is rejected."""
    settings = get_settings()
    user_id = uuid7()
    now = utc_now()

    payload = {
        "sub": str(user_id),
        "sid": str(uuid7()),
        "university_id": str(uuid7()),
        "roles": ["STUDENT"],
        "typ": "access",
        "jti": str(uuid7()),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "iss": settings.AUTH_ISSUER,
        "aud": "different-audience",
    }
    token = jwt.encode(payload, settings.AUTH_SIGNING_KEY, algorithm=settings.AUTH_ALGORITHM)

    with pytest.raises(TokenInvalidException):
        decode_access_token(token)


def test_access_token_wrong_type_rejection() -> None:
    """Verify non-access token type is rejected."""
    settings = get_settings()
    user_id = uuid7()
    now = utc_now()

    payload = {
        "sub": str(user_id),
        "sid": str(uuid7()),
        "university_id": str(uuid7()),
        "roles": ["STUDENT"],
        "typ": "refresh",  # Incorrect typ
        "jti": str(uuid7()),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "iss": settings.AUTH_ISSUER,
        "aud": settings.AUTH_AUDIENCE,
    }
    token = jwt.encode(payload, settings.AUTH_SIGNING_KEY, algorithm=settings.AUTH_ALGORITHM)

    with pytest.raises(TokenInvalidException, match="Expected access token"):
        decode_access_token(token)


def test_refresh_token_generation_and_hashing() -> None:
    """Verify opaque refresh token has high entropy and matches deterministic SHA-256 hash."""
    raw_token, token_hash = generate_refresh_token()

    assert len(raw_token) >= 64
    assert len(token_hash) == 64
    assert hash_refresh_token(raw_token) == token_hash

    # Different tokens generate distinct hashes
    raw_token_2, token_hash_2 = generate_refresh_token()
    assert raw_token != raw_token_2
    assert token_hash != token_hash_2
