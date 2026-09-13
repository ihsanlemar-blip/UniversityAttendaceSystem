"""Typed configuration management using Pydantic Settings.

Supports twelve-factor app configuration via environment variables,
with strict validation, fail-fast defaults, and clear category separation.
"""

from functools import lru_cache

from backend.app.core.constants import DEFAULT_LOCALE, DEFAULT_TIMEZONE, Environment
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """System-wide application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # =========================================================================
    # 1. APP Settings
    # =========================================================================
    APP_ENV: Environment = Field(default=Environment.DEVELOPMENT)
    APP_NAME: str = Field(default="University Attendance System")
    APP_VERSION: str = Field(default="0.1.0")
    DEBUG: bool = Field(default=False)

    UNIVERSITY_ID: str = Field(default="00000000-0000-0000-0000-000000000001")
    UNIVERSITY_NAME: str = Field(default="Kabul University")
    UNIVERSITY_TIMEZONE: str = Field(default=DEFAULT_TIMEZONE)
    DEFAULT_LOCALE: str = Field(default=DEFAULT_LOCALE)

    # =========================================================================
    # 2. DATABASE Settings (PostgreSQL)
    # =========================================================================
    DATABASE_HOST: str = Field(default="localhost")
    DATABASE_PORT: int = Field(default=5432)
    DATABASE_NAME: str = Field(default="attendance_db")
    DATABASE_USER: str = Field(default="attendance_user")
    DATABASE_PASSWORD: str = Field(default="dev_insecure_password")
    DATABASE_POOL_SIZE: int = Field(default=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=10)
    DATABASE_SSL_MODE: str = Field(default="disable")

    # Optional explicit override for database URL
    DATABASE_URL: str | None = Field(default=None)

    @property
    def async_database_url(self) -> str:
        """Construct the async SQLAlchemy connection URL."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            if url.startswith("postgres://"):
                return url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@"
            f"{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    # =========================================================================
    # 3. REDIS & CELERY Settings
    # =========================================================================
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")

    # =========================================================================
    # 4. AUTH Placeholders (Deferred to Milestone 5)
    # =========================================================================
    AUTH_SIGNING_KEY: str = Field(default="dev_insecure_jwt_signing_key_do_not_use_in_production")
    AUTH_ACCESS_TOKEN_MINUTES: int = Field(default=15)
    AUTH_REFRESH_TOKEN_DAYS: int = Field(default=7)
    AUTH_PASSWORD_HASH_ALGO: str = Field(default="argon2id")
    AUTH_MAX_LOGIN_ATTEMPTS: int = Field(default=5)

    # =========================================================================
    # 5. ATTENDANCE Defaults (ADR-010)
    # =========================================================================
    ATTENDANCE_TOKEN_ROTATION_SECONDS: int = Field(default=30)
    ATTENDANCE_TOKEN_TOLERANCE_STEPS: int = Field(default=1)
    ATTENDANCE_DEFAULT_CHECKPOINT_SECONDS: int = Field(default=300)
    ATTENDANCE_LATE_THRESHOLD_MINUTES: int = Field(default=10)
    ATTENDANCE_MINIMUM_PERCENTAGE: float = Field(default=75.0)
    ATTENDANCE_TOKEN_HMAC_SECRET: str = Field(
        default="dev_insecure_qr_hmac_secret_do_not_use_in_prod"
    )

    # =========================================================================
    # 6. NETWORK Settings
    # =========================================================================
    CAMPUS_TRUSTED_SUBNETS: str = Field(default="192.168.0.0/16,10.0.0.0/8")
    CAMPUS_NETWORK_CHECK_ENABLED: bool = Field(default=True)

    # =========================================================================
    # 7. CLOUD SYNC & BACKUP Placeholders
    # =========================================================================
    CLOUD_SYNC_ENABLED: bool = Field(default=False)
    CLOUD_SYNC_URL: str = Field(default="https://cloud.university.edu/api/v1/sync")
    CLOUD_SYNC_API_KEY: str = Field(default="placeholder_cloud_sync_api_key")
    CLOUD_SYNC_BATCH_SIZE: int = Field(default=100)

    BACKUP_ENABLED: bool = Field(default=True)
    BACKUP_PATH: str = Field(default="/var/backups/attendance")
    BACKUP_RETENTION_DAYS: int = Field(default=30)

    # =========================================================================
    # 8. LOGGING Settings
    # =========================================================================
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")

    # =========================================================================
    # 9. CORS & Web Client Settings
    # =========================================================================
    CORS_ALLOWED_ORIGINS: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")
    PUBLIC_WEB_BASE_URL: str = Field(default="http://localhost:3000")
    LOCAL_SERVER_BASE_URL: str = Field(default="http://localhost:8000")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        if not self.CORS_ALLOWED_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    @field_validator("CORS_ALLOWED_ORIGINS")
    @classmethod
    def validate_cors(cls, v: str) -> str:
        """Prevent unsafe wildcard CORS with credentials."""
        origins = [o.strip() for o in v.split(",") if o.strip()]
        if "*" in origins and len(origins) > 1:
            raise ValueError("Wildcard '*' cannot be combined with specific origins.")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
