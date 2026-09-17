"""Domain and application exceptions mapping to standard HTTP error envelopes."""

from typing import Any

from fastapi import status


class DomainException(Exception):
    """Base domain exception for all expected business errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundException(DomainException):
    """Resource not found."""

    def __init__(
        self,
        entity: str,
        identifier: Any,
        message: str | None = None,
    ) -> None:
        msg = message or f"{entity} with identifier '{identifier}' was not found."
        super().__init__(
            code="NOT_FOUND",
            message=msg,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"entity": entity, "identifier": str(identifier)},
        )


class ValidationException(DomainException):
    """Input validation failure."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details=details,
        )


class UnauthorizedException(DomainException):
    """Authentication required or failed."""

    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenException(DomainException):
    """Insufficient privileges."""

    def __init__(self, message: str = "Access forbidden.") -> None:
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class MetricsAccessForbiddenException(DomainException):
    """Operational metrics endpoint access restricted."""

    def __init__(
        self,
        message: str = (
            "Access to operational metrics is restricted to internal monitoring "
            "networks or authenticated monitoring requests."
        ),
    ) -> None:
        super().__init__(
            code="METRICS_ACCESS_FORBIDDEN",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ConflictException(DomainException):
    """State conflict or duplicate entry."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        code: str = "CONFLICT",
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class InfrastructureException(DomainException):
    """Internal service or dependency failure (DB, Redis)."""

    def __init__(
        self,
        message: str = "An internal dependency error occurred.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="INFRASTRUCTURE_ERROR",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class RateLimitExceededException(DomainException):
    """Too many requests rate limit exceeded (HTTP 429)."""

    def __init__(
        self,
        retry_after: int,
        message: str = "Too many requests. Please try again later.",
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = dict(details or {})
        merged["retry_after"] = retry_after
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=merged,
        )
        self.retry_after = retry_after
