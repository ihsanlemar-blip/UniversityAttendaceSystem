"""Unit tests for configuration management (backend/app/core/config.py)."""

import pytest

from backend.app.core.config import Settings
from backend.app.core.constants import Environment


def test_default_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify default settings values match architecture baseline."""
    monkeypatch.delenv("APP_ENV", raising=False)
    settings = Settings()

    assert settings.APP_NAME == "University Attendance System"
    assert settings.APP_VERSION == "0.1.0"
    assert settings.APP_ENV == Environment.DEVELOPMENT
    assert settings.DATABASE_PORT == 5432
    assert settings.DATABASE_NAME == "attendance_db"
    assert settings.ATTENDANCE_TOKEN_ROTATION_SECONDS == 30
    assert settings.ATTENDANCE_TOKEN_TOLERANCE_STEPS == 1
    assert settings.ATTENDANCE_MINIMUM_PERCENTAGE == 75.0


def test_async_database_url_generation() -> None:
    """Verify async database URL formatting with default and override URLs."""
    settings = Settings(
        DATABASE_USER="test_user",
        DATABASE_PASSWORD="test_password",
        DATABASE_HOST="db.local",
        DATABASE_PORT=5433,
        DATABASE_NAME="test_db",
    )
    expected = "postgresql+asyncpg://test_user:test_password@db.local:5433/test_db"
    assert settings.async_database_url == expected


def test_async_database_url_normalization() -> None:
    """Verify postgresql:// and postgres:// URLs are normalized to postgresql+asyncpg://."""
    settings_pg = Settings(DATABASE_URL="postgresql://user:pass@host:5432/db")
    assert settings_pg.async_database_url == "postgresql+asyncpg://user:pass@host:5432/db"

    settings_postgres = Settings(DATABASE_URL="postgres://user:pass@host:5432/db")
    assert settings_postgres.async_database_url == "postgresql+asyncpg://user:pass@host:5432/db"

    settings_direct = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db")
    assert settings_direct.async_database_url == "postgresql+asyncpg://user:pass@host:5432/db"


def test_cors_origins_parsing() -> None:
    """Verify CORS origins string is split into clean list."""
    settings = Settings(CORS_ALLOWED_ORIGINS="http://localhost:3000, https://attendance.uni.edu ")
    assert settings.cors_origins_list == [
        "http://localhost:3000",
        "https://attendance.uni.edu",
    ]


def test_cors_origins_wildcard_validation() -> None:
    """Verify combining wildcard with specific origins raises ValueError."""
    with pytest.raises(ValueError, match="Wildcard"):
        Settings(CORS_ALLOWED_ORIGINS="*, http://localhost:3000")


def test_future_secrets_optional_when_features_disabled() -> None:
    """Verify future secrets may remain absent when corresponding features are disabled."""
    settings = Settings()
    assert settings.AUTH_SIGNING_KEY is not None
    assert settings.ATTENDANCE_TOKEN_HMAC_SECRET is None
    assert settings.CLOUD_SYNC_API_KEY is None
    assert settings.CLOUD_SYNC_ENABLED is False


def test_cloud_sync_secret_required_when_enabled() -> None:
    """Verify CLOUD_SYNC_API_KEY is required when CLOUD_SYNC_ENABLED is True."""
    with pytest.raises(ValueError, match="CLOUD_SYNC_API_KEY"):
        Settings(CLOUD_SYNC_ENABLED=True, CLOUD_SYNC_API_KEY=None)


def test_cloud_sync_secret_accepted_when_provided() -> None:
    """Verify CLOUD_SYNC_ENABLED succeeds when valid API key is supplied."""
    settings = Settings(CLOUD_SYNC_ENABLED=True, CLOUD_SYNC_API_KEY="sync-secret-key-12345")
    assert settings.CLOUD_SYNC_ENABLED is True
    assert settings.CLOUD_SYNC_API_KEY == "sync-secret-key-12345"


def test_production_rejects_insecure_db_password() -> None:
    """Verify production environment rejects default insecure passwords."""
    with pytest.raises(ValueError, match="Insecure DATABASE_PASSWORD"):
        Settings(
            APP_ENV=Environment.PRODUCTION,
            DATABASE_PASSWORD="dev_insecure_password",
            AUTH_SIGNING_KEY="a-secure-production-key-that-has-at-least-32-characters",
        )


def test_production_rejects_insecure_auth_signing_key() -> None:
    """Verify production environment rejects default or short AUTH_SIGNING_KEY."""
    with pytest.raises(ValueError, match="secure AUTH_SIGNING_KEY"):
        Settings(
            APP_ENV=Environment.PRODUCTION,
            DATABASE_PASSWORD="strong-production-password-123",
            AUTH_SIGNING_KEY="short-key",
        )
