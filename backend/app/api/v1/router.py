"""API Version 1 root router and metadata endpoints."""

from fastapi import APIRouter

from backend.app.common.schemas import ApiMetadataResponse
from backend.app.common.types import utc_now
from backend.app.core.config import get_settings

api_v1_router = APIRouter(prefix="/api/v1", tags=["API v1"])


@api_v1_router.get(
    "/",
    response_model=ApiMetadataResponse,
    summary="API v1 Metadata",
    description="Returns public API versioning and service status information.",
)
async def get_api_v1_metadata() -> ApiMetadataResponse:
    settings = get_settings()
    return ApiMetadataResponse(
        service="Digital Student Attendance API",
        api_version="v1",
        status="operational",
        environment=settings.APP_ENV.value,
        server_time_utc=utc_now().isoformat(),
    )
