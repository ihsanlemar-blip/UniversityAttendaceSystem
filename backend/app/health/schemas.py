"""Health probe request and response schemas."""

from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    """Liveness probe status payload."""

    status: str = Field(default="alive", description="Process liveness status")
    service: str = Field(default="backend", description="Service identifier")
    version: str = Field(default="0.1.0", description="Service semantic version")


class ReadinessResponse(BaseModel):
    """Readiness probe status payload verifying infrastructure dependencies."""

    status: str = Field(description="System readiness: 'ready' or 'unhealthy'")
    service: str = Field(default="backend", description="Service identifier")
    version: str = Field(default="0.1.0", description="Service semantic version")
    dependencies: dict[str, str] = Field(
        description="Individual status of required backing infrastructure"
    )


class MetricsResponse(BaseModel):
    """Observability metrics payload for system monitoring."""

    status: str = Field(default="ok", description="Metrics status")
    uptime_seconds: float = Field(description="Process uptime in seconds")
    db_pool: dict[str, int] = Field(description="Database connection pool statistics")
