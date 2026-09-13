"""Unit tests for configuration management (backend/app/core/config.py)."""

import pytest

from backend.app.core.config import Settings
from backend.app.core.constants import Environment


def test_default_settings() -> None:
    """Verify default settings values match architecture baseline."""
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
