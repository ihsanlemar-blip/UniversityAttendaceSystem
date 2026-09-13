"""Security audit event logging helpers for authentication and authorization."""

import uuid
from typing import Any

from backend.app.common.types import utc_now
from backend.app.core.logging import get_logger

logger = get_logger("security.auth")

# Redaction key set to prevent accidental leak of sensitive materials
FORBIDDEN_LOG_KEYS = {
    "password",
    "password_hash",
    "raw_token",
    "access_token",
    "refresh_token",
    "token",
    "authorization",
    "auth_signing_key",
    "hmac_secret",
}


def sanitize_security_details(details: dict[str, Any] | None) -> dict[str, Any]:
    """Sanitize dictionary to guarantee no sensitive credentials or tokens appear in logs."""
    if not details:
        return {}

    sanitized: dict[str, Any] = {}
    for k, v in details.items():
        if k.lower() in FORBIDDEN_LOG_KEYS:
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_security_details(v)
        else:
            sanitized[k] = v
    return sanitized


def log_security_event(
    event_type: str,
    user_id: uuid.UUID | None = None,
    university_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Emit structured security event log without sensitive credentials."""
    safe_details = sanitize_security_details(details)
    event_data = {
        "security_event": event_type,
        "user_id": str(user_id) if user_id else None,
        "university_id": str(university_id) if university_id else None,
        "timestamp_utc": utc_now().isoformat(),
        **safe_details,
    }

    if event_type in {
        "LOGIN_FAILURE",
        "ACCOUNT_LOCKED",
        "REFRESH_TOKEN_REUSE_DETECTED",
        "PERMISSION_DENIED",
    }:
        logger.warning(f"Security event: {event_type}", extra=event_data)
    else:
        logger.info(f"Security event: {event_type}", extra=event_data)
