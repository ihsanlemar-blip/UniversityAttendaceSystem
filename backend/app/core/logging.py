"""Structured JSON logging with request correlation IDs and sensitive data redaction."""

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Context variable holding correlation request_id for the active async task
request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Regular expressions for detecting and redacting sensitive values
SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(password|secret|token|key|auth|bearer)[\"':\s=]+([^\s\"',]+)"),
    re.compile(r"Bearer\s+([a-zA-Z0-9\._-]+)"),
]


def redact_sensitive_info(text: str) -> str:
    """Redact passwords, tokens, and authorization credentials from log messages."""
    redacted = text
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub(r"\1: [REDACTED]", redacted)
    return redacted


class JSONFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def __init__(self, service: str = "backend", env: str = "development") -> None:
        super().__init__()
        self.service = service
        self.env = env

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_sensitive_info(record.getMessage()),
            "service": self.service,
            "environment": self.env,
            "request_id": request_id_ctx_var.get() or "-",
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(level: str = "INFO", json_format: bool = True, env: str = "development") -> None:
    """Configure system-wide root and application loggers."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    if json_format:
        stream_handler.setFormatter(JSONFormatter(service="backend", env=env))
    else:
        stream_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] [%(name)s] [req:%(request_id)s] %(message)s"
            )
        )

    root_logger.addHandler(stream_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance with designated name."""
    return logging.getLogger(name)
