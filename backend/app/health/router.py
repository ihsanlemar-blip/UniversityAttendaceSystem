import time

from fastapi import APIRouter, Depends, Header, Request, Response, status

from backend.app.core.config import get_settings
from backend.app.core.constants import Environment
from backend.app.core.database import get_engine
from backend.app.core.exceptions import MetricsAccessForbiddenException
from backend.app.core.logging import get_logger
from backend.app.health.schemas import LivenessResponse, MetricsResponse, ReadinessResponse
from backend.app.health.service import HealthService
from backend.app.security.resolver import ClientNetworkResolver

logger = get_logger(__name__)
_start_time = time.time()
router = APIRouter(tags=["Health"])


async def verify_metrics_access(
    request: Request,
    x_metrics_key: str | None = Header(None, alias="X-Metrics-Key"),
) -> None:
    """Authorize access to operational / metrics endpoints.

    Permits access if:
    1. A valid X-Metrics-Key header or Bearer token matching METRICS_ACCESS_KEY is provided.
    2. In dev/test mode and request originates from localhost/testclient.
    3. Resolved client IP matches METRICS_ALLOWED_CIDRS (trusted monitoring / internal subnet).
    Otherwise raises HTTP 403 Forbidden.
    """
    settings = get_settings()

    # 1. Check explicit metrics key / token
    auth_header = request.headers.get("Authorization", "")
    bearer_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else None
    provided_key = x_metrics_key or bearer_token

    if settings.METRICS_ACCESS_KEY and provided_key == settings.METRICS_ACCESS_KEY:
        return

    # 2. In development or testing without an explicit key, allow local/testclient calls
    client_host = request.client.host if request.client else ""
    if settings.APP_ENV in (Environment.DEVELOPMENT, Environment.TESTING):
        if not settings.METRICS_ACCESS_KEY:
            return
        if client_host in ("testclient", "127.0.0.1", "::1", "localhost"):
            return

    # 3. Resolve effective client IP across trusted proxies
    effective_ip, _, _ = ClientNetworkResolver.extract_effective_client_ip(
        request, trusted_proxy_cidrs=settings.TRUSTED_PROXY_CIDRS
    )

    allowed_networks = ClientNetworkResolver.parse_cidr_list(settings.METRICS_ALLOWED_CIDRS)
    if ClientNetworkResolver.is_ip_in_cidrs(effective_ip, allowed_networks):
        return

    raise MetricsAccessForbiddenException()


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
    dependencies=[Depends(verify_metrics_access)],
    summary="Observability Metrics Probe",
)
@router.get(
    "/metrics",
    response_model=MetricsResponse,
    dependencies=[Depends(verify_metrics_access)],
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
