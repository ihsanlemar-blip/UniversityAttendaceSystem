"""Health probe HTTP endpoints."""

from fastapi import APIRouter, Response, status

from backend.app.core.config import get_settings
from backend.app.health.schemas import LivenessResponse, ReadinessResponse
from backend.app.health.service import HealthService

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


health_router = router
