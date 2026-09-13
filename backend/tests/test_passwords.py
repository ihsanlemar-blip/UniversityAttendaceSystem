"""Unit tests for Argon2id password hashing, verification, and policy enforcement."""

import pytest

from backend.app.auth.passwords import (
    hash_password,
    validate_password_policy,
    verify_password,
)
from backend.app.core.exceptions import ValidationException


def test_password_hashing_creates_argon2id_hash() -> None:
    """Verify passwords are encrypted using modern Argon2id hash format."""
    raw = "StrongInstitutionalPassword123!"
    pw_hash = hash_password(raw)

    assert pw_hash != raw
    assert pw_hash.startswith("$argon2id$")


def test_password_verification_success() -> None:
    """Verify correct password verifies successfully."""
    raw = "ValidPassword456@"
    pw_hash = hash_password(raw)

    is_valid, updated_hash = verify_password(raw, pw_hash)
    assert is_valid is True
    assert updated_hash is None


def test_password_verification_failure() -> None:
    """Verify incorrect password fails verification."""
    pw_hash = hash_password("CorrectPassword123!")

    is_valid, _ = verify_password("WrongPassword123!", pw_hash)
    assert is_valid is False


def test_password_verification_with_empty_inputs() -> None:
    """Verify empty inputs return False without crashing."""
    is_valid, _ = verify_password("", "")
    assert is_valid is False

    is_valid, _ = verify_password("something", "")
    assert is_valid is False

    is_valid, _ = verify_password("", "$argon2id$...")
    assert is_valid is False


def test_password_policy_minimum_length() -> None:
    """Verify passwords shorter than configured minimum length are rejected."""
    with pytest.raises(ValidationException, match="at least 8 characters"):
        validate_password_policy("short")


def test_password_policy_maximum_length() -> None:
    """Verify oversized passwords (>128 chars) are rejected to prevent DoS."""
    oversized = "a" * 129
    with pytest.raises(ValidationException, match="cannot exceed 128 characters"):
        validate_password_policy(oversized)


def test_password_policy_empty_rejected() -> None:
    """Verify empty passwords are rejected."""
    with pytest.raises(ValidationException, match="cannot be empty"):
        validate_password_policy("")


def test_password_preserves_full_unicode() -> None:
    """Verify passwords with non-ASCII and Unicode characters hash and verify accurately."""
    unicode_pw = "د_پوهنتون_پټ_نوم_1234#!"  # Pashto unicode text
    pw_hash = hash_password(unicode_pw)

    assert pw_hash.startswith("$argon2id$")
    is_valid, _ = verify_password(unicode_pw, pw_hash)
    assert is_valid is True

    # Mutated unicode fails
    is_valid_bad, _ = verify_password("د_پوهنتون_پټ_نوم_1234#!_wrong", pw_hash)
    assert is_valid_bad is False
