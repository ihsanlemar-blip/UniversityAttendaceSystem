import time

from fastapi import APIRouter, Response, status

from backend.app.core.config import get_settings
from backend.app.core.database import get_engine
from backend.app.core.logging import get_logger
from backend.app.health.schemas import LivenessResponse, MetricsResponse, ReadinessResponse
from backend.app.health.service import HealthService

logger = get_logger(__name__)
_start_time = time.time()
router = APIRouter(tags=["Health"])


@router.get(
    "/health/live",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Confirms that the FastAPI process is running and accepting HTTP requests.",
)
async def liveness() -> LivenessResponse:
    settings = get_settings()
    return LivenessResponse(
        status="alive",
        service="backend",
        version=settings.APP_VERSION,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness Probe",
    description="Verifies reachability of core infrastructure dependencies (PostgreSQL, Redis).",
)
async def readiness(response: Response) -> ReadinessResponse:
    settings = get_settings()
    is_ready, dependencies = await HealthService.evaluate_readiness()

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if is_ready else "unhealthy",
        service="backend",
        version=settings.APP_VERSION,
        dependencies=dependencies,
    )


@router.get(
    "/health/metrics",
    response_model=MetricsResponse,
    summary="Observability Metrics Probe",
)
@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Prometheus / Observability Metrics",
)
async def metrics() -> MetricsResponse:
    """Return process uptime and database connection pool diagnostics."""
    uptime = time.time() - _start_time
    pool_stats: dict[str, int] = {"size": 0, "checked_in": 0, "checked_out": 0, "overflow": 0}
    try:
        engine = get_engine()
        pool = engine.pool
        pool_stats = {
            "size": int(getattr(pool, "size", lambda: 0)()),
            "checked_in": int(getattr(pool, "checkedin", lambda: 0)()),
            "checked_out": int(getattr(pool, "checkedout", lambda: 0)()),
            "overflow": int(getattr(pool, "overflow", lambda: 0)()),
        }
    except Exception as exc:
        logger.debug("Database connection pool metrics collection skipped: %s", exc)
    return MetricsResponse(
        status="ok",
        uptime_seconds=round(uptime, 2),
        db_pool=pool_stats,
    )


health_router = router
