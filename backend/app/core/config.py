"""Typed configuration management using Pydantic Settings.

Supports twelve-factor app configuration via environment variables,
with strict validation, fail-fast defaults, and clear category separation.
"""

from functools import lru_cache

from backend.app.core.constants import DEFAULT_LOCALE, DEFAULT_TIMEZONE, Environment
from pydantic import Field, field_validator, model_validator
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
    DOCS_ENABLED: bool | None = Field(
        default=None,
        description=(
            "Enable Swagger UI, ReDoc, and OpenAPI documentation endpoints. "
            "Defaults to False in production, True in development and testing."
        ),
    )

    @property
    def is_docs_enabled(self) -> bool:
        """Determine whether Swagger and OpenAPI documentation are enabled."""
        if self.DOCS_ENABLED is not None:
            return self.DOCS_ENABLED
        return self.APP_ENV != Environment.PRODUCTION

    UNIVERSITY_ID: str = Field(default="00000000-0000-0000-0000-000000000001")
    UNIVERSITY_NAME: str = Field(default="Kabul University")
    UNIVERSITY_TIMEZONE: str = Field(default=DEFAULT_TIMEZONE)
    DEFAULT_LOCALE: str = Field(default=DEFAULT_LOCALE)

    # =========================================================================
    # 2. DATABASE Settings (PostgreSQL)
    # =========================================================================
    DATABASE_HOST: str = Field(default="127.0.0.1")
    DATABASE_PORT: int = Field(default=5432)
    DATABASE_NAME: str = Field(default="attendance_db")
    DATABASE_USER: str = Field(default="attendance_user")
    DATABASE_PASSWORD: str = Field(default="dev_insecure_password")
    DATABASE_POOL_SIZE: int = Field(default=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=10)
    DATABASE_POOL_TIMEOUT: int = Field(default=30)
    DATABASE_POOL_RECYCLE: int = Field(default=1800)
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
    REDIS_URL: str = Field(default="redis://127.0.0.1:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://127.0.0.1:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://127.0.0.1:6379/2")

    # =========================================================================
    # 4. AUTH Settings (Milestone 5)
    # =========================================================================
    AUTH_SIGNING_KEY: str = Field(
        default="dev-auth-signing-key-minimum-32-chars-for-testing-purposes-only",
        description="JWT HMAC signing key. Must be cryptographically random and >=32 chars.",
    )
    AUTH_ALGORITHM: str = Field(default="HS256")
    AUTH_ACCESS_TOKEN_MINUTES: int = Field(default=15)
    AUTH_REFRESH_TOKEN_DAYS: int = Field(default=7)
    AUTH_PASSWORD_HASH_ALGO: str = Field(default="argon2id")
    AUTH_PASSWORD_MIN_LENGTH: int = Field(default=8)
    AUTH_PASSWORD_MAX_LENGTH: int = Field(default=128)
    AUTH_PASSWORD_REQUIRE_COMPOSITION: bool = Field(default=False)
    AUTH_MAX_LOGIN_ATTEMPTS: int = Field(default=5)
    AUTH_LOCKOUT_DURATION_MINUTES: int = Field(default=15)
    AUTH_ISSUER: str = Field(default="university-attendance-api")
    AUTH_AUDIENCE: str = Field(default="university-attendance-client")

    # =========================================================================
    # 5. ATTENDANCE & Dynamic QR Defaults (Milestone 10)
    # =========================================================================
    ATTENDANCE_QR_ENABLED: bool = Field(default=True)
    ATTENDANCE_QR_SIGNING_KEY: str = Field(
        default="dev-attendance-qr-signing-key-minimum-32-chars-for-testing-only",
        description=(
            "Dedicated HMAC signing key for attendance QR tokens. Isolated from AUTH_SIGNING_KEY."
        ),
    )
    ATTENDANCE_QR_SIGNING_KID: str = Field(default="att-qr-k1")
    ATTENDANCE_QR_ISSUER: str = Field(default="digital-student-attendance-system")
    ATTENDANCE_QR_AUDIENCE: str = Field(default="attendance-checkpoint")
    ATTENDANCE_QR_ROTATION_SECONDS: int = Field(default=30)
    ATTENDANCE_TOKEN_ROTATION_SECONDS: int = Field(default=30)
    ATTENDANCE_TOKEN_TOLERANCE_STEPS: int = Field(default=1)
    ATTENDANCE_DEFAULT_CHECKPOINT_SECONDS: int = Field(default=300)
    ATTENDANCE_LATE_THRESHOLD_MINUTES: int = Field(default=10)
    ATTENDANCE_MINIMUM_PERCENTAGE: float = Field(default=75.0)
    ATTENDANCE_TOKEN_HMAC_SECRET: str | None = Field(
        default=None,
        description="Legacy alias / optional auxiliary secret.",
    )

    # =========================================================================
    # 5.1 ATTENDANCE & Bluetooth BLE Defaults (Milestone 11)
    # =========================================================================
    ATTENDANCE_BLE_ENABLED: bool = Field(default=True)
    ATTENDANCE_BLE_SIGNING_KEY: str = Field(
        default="dev-attendance-ble-signing-key-minimum-32-chars-for-testing-only",
        description=(
            "Dedicated HMAC signing key for attendance BLE presence tokens. "
            "Strictly isolated from AUTH_SIGNING_KEY and ATTENDANCE_QR_SIGNING_KEY."
        ),
    )
    ATTENDANCE_BLE_PROTOCOL_VERSION: int = Field(default=1)
    ATTENDANCE_BLE_SERVICE_UUID: str = Field(
        default="0000fee0-0000-1000-8000-00805f9b34fb",
        description="Standard 128-bit service UUID advertised by classroom BLE broadcasters.",
    )
    ATTENDANCE_BLE_ROTATION_SECONDS: int = Field(default=20)
    ATTENDANCE_BLE_MIN_RSSI: int | None = Field(
        default=-85,
        description=(
            "Optional minimum RSSI (dBm) threshold for BLE proximity validation. Default -85 dBm."
        ),
    )

    # =========================================================================
    # 5.2 ATTENDANCE & Offline Attendance Defaults (Milestone 12)
    # =========================================================================
    ATTENDANCE_OFFLINE_ENABLED: bool = Field(default=True)
    OFFLINE_PERMIT_SIGNING_PRIVATE_KEY: str = Field(
        default=(
            "-----BEGIN " + "PRIVATE KEY-----\n"
            "MC4CAQAwBQYDK2VwBCIEINmqhHd4Uz7002Yt007zEIPHYaMaPH6civdsgT9jiyMY\n"
            "-----END " + "PRIVATE KEY-----"
        ),
        description=(
            "Dedicated Ed25519 private key in PEM format used to sign offline permits. "
            "Isolated from AUTH_SIGNING_KEY, ATTENDANCE_QR_SIGNING_KEY, and "
            "ATTENDANCE_BLE_SIGNING_KEY."
        ),
    )
    OFFLINE_PERMIT_SIGNING_PUBLIC_KEY: str = Field(
        default=(
            "-----BEGIN " + "PUBLIC KEY-----\n"
            "MCowBQYDK2VwAyEAXHamr+uJLTuybQnRkB8K2lNMsueoewuYJ0O0d/OhlRo=\n"
            "-----END " + "PUBLIC KEY-----"
        ),
        description=(
            "Dedicated Ed25519 public key in PEM format used to verify offline attendance permits."
        ),
    )
    OFFLINE_PERMIT_SIGNING_KID: str = Field(default="att-off-k1")
    ATTENDANCE_OFFLINE_MAX_VALIDITY_HOURS: int = Field(default=24)
    ATTENDANCE_OFFLINE_ROTATION_SECONDS: int = Field(default=20)
    ATTENDANCE_OFFLINE_MAX_CLOCK_DRIFT_SECONDS: int = Field(default=300)

    # =========================================================================
    # 5.3 DEVICE TRUST & PRIMARY DEVICE BINDING (Milestone 13)
    # =========================================================================
    ATTENDANCE_DEVICE_TRUST_ENABLED: bool = Field(
        default=True,
        description="Enforce primary device trust for student attendance check-ins.",
    )
    DEVICE_REGISTRATION_CHALLENGE_LIFETIME_SECONDS: int = Field(
        default=300,
        description="Lifetime of device registration challenge in seconds (default 5 minutes).",
    )

    # =========================================================================
    # 6. NETWORK & Anti-Cheat Presence Settings (Milestone 14)
    # =========================================================================
    CAMPUS_TRUSTED_SUBNETS: str = Field(default="192.168.0.0/16,10.0.0.0/8")
    CAMPUS_NETWORK_CHECK_ENABLED: bool = Field(default=True)
    TRUSTED_PROXY_CIDRS: str = Field(
        default="127.0.0.1/32,::1/128",
        description=(
            "Comma-separated CIDRs of trusted reverse proxies allowed to set"
            " forwarded client headers."
        ),
    )
    ATTENDANCE_NETWORK_CHALLENGE_TTL_SECONDS: int = Field(
        default=20,
        description=(
            "Lifetime of short-lived campus network presence challenge in seconds (default 20s)."
        ),
    )
    ATTENDANCE_ANTI_CHEAT_ENABLED: bool = Field(
        default=True,
        description="Enable anti-cheat signal detection and audit logging.",
    )
    RATE_LIMITING_ENABLED: bool = Field(
        default=True,
        description="Enable or disable API rate limiting globally.",
    )
    ANTI_CHEAT_REPLACEMENT_THRESHOLD_COUNT: int = Field(
        default=2,
        description=(
            "Approved device replacements count in rolling window triggering high frequency signal."
        ),
    )
    ANTI_CHEAT_REPLACEMENT_WINDOW_DAYS: int = Field(
        default=30,
        description="Rolling window days for device replacement frequency check.",
    )
    ANTI_CHEAT_MANUAL_RATE_THRESHOLD_PERCENT: float = Field(
        default=30.0,
        description=(
            "Percentage of roster manually credited triggering manual attendance rate signal."
        ),
    )
    ANTI_CHEAT_MASS_MANUAL_COUNT_THRESHOLD: int = Field(
        default=15,
        description=(
            "Single-actor manual attendance count in session triggering mass manual signal."
        ),
    )
    ANTI_CHEAT_CORRECTION_RATE_THRESHOLD_PERCENT: float = Field(
        default=20.0,
        description="Percentage of session records revised triggering high correction rate signal.",
    )
    ANTI_CHEAT_SCHEDULE_DEVIATION_MINUTES: int = Field(
        default=60,
        description=(
            "Minutes deviation from scheduled occurrence start triggering schedule window signal."
        ),
    )

    # =========================================================================
    # 7. CLOUD SYNC & BACKUP Placeholders
    # =========================================================================
    CLOUD_SYNC_ENABLED: bool = Field(default=False)
    CLOUD_SYNC_URL: str = Field(default="https://cloud.university.edu/api/v1/sync")
    CLOUD_SYNC_API_KEY: str | None = Field(
        default=None,
        description=(
            "API key for central cloud synchronization. Required when CLOUD_SYNC_ENABLED=True."
        ),
    )
    CLOUD_SYNC_BATCH_SIZE: int = Field(default=100)

    BACKUP_ENABLED: bool = Field(default=True)
    BACKUP_PATH: str = Field(default="/var/backups/attendance")
    BACKUP_RETENTION_DAYS: int = Field(default=30)

    # =========================================================================
    # 8. OBSERVABILITY & Metrics Protection
    # =========================================================================
    METRICS_ACCESS_KEY: str | None = Field(
        default=None,
        description=(
            "Secret token or API key required to access /metrics and /health/metrics. "
            "If unset in production, access is restricted strictly to trusted internal subnets."
        ),
    )
    METRICS_ALLOWED_CIDRS: str = Field(
        default="127.0.0.1/32,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
        description=(
            "Comma-separated list of CIDR subnets allowed to access metrics endpoints "
            "without explicit API key."
        ),
    )

    @model_validator(mode="after")
    def validate_cross_field_dependencies(self) -> Settings:
        """Enforce conditional secret requirements and production security."""
        if self.CLOUD_SYNC_ENABLED and not self.CLOUD_SYNC_API_KEY:
            raise ValueError("CLOUD_SYNC_API_KEY is required when CLOUD_SYNC_ENABLED is True.")

        if self.ATTENDANCE_QR_ENABLED and self.ATTENDANCE_QR_SIGNING_KEY == self.AUTH_SIGNING_KEY:
            raise ValueError(
                "ATTENDANCE_QR_SIGNING_KEY must be distinct from AUTH_SIGNING_KEY "
                "(cryptographic separation)."
            )

        if self.ATTENDANCE_BLE_ENABLED:
            if (
                self.ATTENDANCE_BLE_SIGNING_KEY == self.AUTH_SIGNING_KEY
                or self.ATTENDANCE_BLE_SIGNING_KEY == self.ATTENDANCE_QR_SIGNING_KEY
            ):
                raise ValueError(
                    "ATTENDANCE_BLE_SIGNING_KEY must be distinct from AUTH_SIGNING_KEY and "
                    "ATTENDANCE_QR_SIGNING_KEY (cryptographic separation)."
                )

        if self.ATTENDANCE_OFFLINE_ENABLED:
            if (
                self.OFFLINE_PERMIT_SIGNING_PRIVATE_KEY == self.AUTH_SIGNING_KEY
                or self.OFFLINE_PERMIT_SIGNING_PRIVATE_KEY == self.ATTENDANCE_QR_SIGNING_KEY
                or self.OFFLINE_PERMIT_SIGNING_PRIVATE_KEY == self.ATTENDANCE_BLE_SIGNING_KEY
            ):
                raise ValueError(
                    "OFFLINE_PERMIT_SIGNING_PRIVATE_KEY must be distinct from other signing keys "
                    "(cryptographic separation)."
                )

        if self.APP_ENV == Environment.PRODUCTION:
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production environment.")
            if "*" in self.cors_origins_list:
                raise ValueError(
                    "Wildcard '*' CORS origin is strictly forbidden in production environment."
                )
            insecure_passwords = {
                "change_me_in_production",
                "dev_insecure_password",
                "password",
                "secret",
                "changeme",
                "admin",
                "123456",
                "root",
                "toor",
                "test",
                "guest",
                "development",
                "attendance_password",
            }
            if self.DATABASE_PASSWORD.lower() in insecure_passwords:
                raise ValueError(
                    "Insecure DATABASE_PASSWORD default is forbidden in production environment."
                )
            insecure_keys = {
                "dev-auth-signing-key-minimum-32-chars-for-testing-purposes-only",
                "dev-attendance-qr-signing-key-minimum-32-chars-for-testing-only",
                "dev-attendance-ble-signing-key-minimum-32-chars-for-testing-only",
                (
                    "-----BEGIN "
                    + "PRIVATE KEY-----\n"
                    + "MC4CAQAwBQYDK2VwBCIEINmqhHd4Uz7002Yt007zEIPHYaMaPH6civdsgT9jiyMY\n"
                    + "-----END "
                    + "PRIVATE KEY-----"
                ),
                "change_me_in_production",
                "secret",
                "jwt_secret",
            }
            if (
                not self.AUTH_SIGNING_KEY
                or self.AUTH_SIGNING_KEY in insecure_keys
                or len(self.AUTH_SIGNING_KEY) < 32
            ):
                raise ValueError(
                    "A secure AUTH_SIGNING_KEY of at least 32 characters is required in production."
                )
            if self.ATTENDANCE_QR_ENABLED and (
                not self.ATTENDANCE_QR_SIGNING_KEY
                or self.ATTENDANCE_QR_SIGNING_KEY in insecure_keys
                or len(self.ATTENDANCE_QR_SIGNING_KEY) < 32
            ):
                raise ValueError(
                    "A secure ATTENDANCE_QR_SIGNING_KEY of at least 32 characters is required "
                    "in production."
                )
            if self.ATTENDANCE_BLE_ENABLED and (
                not self.ATTENDANCE_BLE_SIGNING_KEY
                or self.ATTENDANCE_BLE_SIGNING_KEY in insecure_keys
                or len(self.ATTENDANCE_BLE_SIGNING_KEY) < 32
            ):
                raise ValueError(
                    "A secure ATTENDANCE_BLE_SIGNING_KEY of at least 32 characters is required "
                    "in production."
                )
            if self.ATTENDANCE_OFFLINE_ENABLED and (
                not self.OFFLINE_PERMIT_SIGNING_PRIVATE_KEY
                or self.OFFLINE_PERMIT_SIGNING_PRIVATE_KEY in insecure_keys
            ):
                raise ValueError(
                    "A secure OFFLINE_PERMIT_SIGNING_PRIVATE_KEY is required in production."
                )

        return self

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

    # =========================================================================
    # 10. IMPORT PIPELINE Settings (Milestone 16)
    # =========================================================================
    IMPORT_MAX_FILE_BYTES: int = Field(
        default=10 * 1024 * 1024,  # 10 MB limit
        description="Maximum upload size in bytes for CSV/XLSX imports.",
    )
    IMPORT_MAX_ROWS: int = Field(
        default=5000,
        description="Maximum allowed rows in an import file.",
    )
    IMPORT_DEFAULT_COMMIT_MODE: str = Field(
        default="STRICT",
        description="Default commit mode: STRICT (block if any error) or PARTIAL.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
