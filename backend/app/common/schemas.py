"""Standard API request and response schemas."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorBody(BaseModel):
    """Structured error payload compliant with docs/10_API_SPECIFICATION.md."""

    code: str = Field(description="Machine-readable uppercase error code")
    message: str = Field(description="Human-readable description of error")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Context-specific error details"
    )
    request_id: str = Field(default="-", description="Correlation request identifier")


class StandardErrorResponse(BaseModel):
    """Standard top-level error response envelope."""

    error: ErrorBody


class StandardResponse(BaseModel, Generic[T]):
    """Standard top-level success response envelope."""

    data: T
    meta: dict[str, Any] | None = None


class ApiMetadataResponse(BaseModel):
    """Root /api/v1 service identification metadata."""

    service: str
    api_version: str
    status: str
    environment: str
    server_time_utc: str
