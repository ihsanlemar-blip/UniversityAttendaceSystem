"""System-wide core constants and status enums."""

from enum import StrEnum


class Environment(StrEnum):
    """Execution environment mode."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class RecordStatus(StrEnum):
    """Generic active status for institutional entities."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    SUSPENDED = "SUSPENDED"


# HTTP and Header Constants
HEADER_REQUEST_ID = "X-Request-ID"
DEFAULT_TIMEZONE = "Asia/Kabul"
DEFAULT_LOCALE = "en"
API_V1_STR = "/api/v1"
