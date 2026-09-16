"""API Version 1 root router and metadata endpoints."""

from fastapi import APIRouter

from backend.app.academic.router import router as academic_router
from backend.app.attendance.operations_router import router as attendance_operations_router
from backend.app.attendance.router import router as attendance_router
from backend.app.attendance.router import students_router as student_attendance_router
from backend.app.auth.router import router as auth_router
from backend.app.calendar.router import academic_years_router, semesters_router
from backend.app.common.schemas import ApiMetadataResponse
from backend.app.common.types import utc_now
from backend.app.core.config import get_settings
from backend.app.curriculum.router import router as curriculum_router
from backend.app.devices.router import router as devices_router
from backend.app.facilities.router import router as facilities_router
from backend.app.offerings.router import router as offerings_router
from backend.app.people.router import router as people_router
from backend.app.rbac.router import router as rbac_router
from backend.app.scheduling.router import router as scheduling_router
from backend.app.security.router import router as security_router
from backend.app.users.router import router as users_router

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


# Mount Milestone 5 Sub-Routers
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(rbac_router)

# Mount Milestone 6 Academic Hierarchy & Calendar Sub-Routers
api_v1_router.include_router(academic_router)
api_v1_router.include_router(academic_years_router)
api_v1_router.include_router(semesters_router)

# Mount Milestone 7 Curriculum, People, Offerings & Rosters Sub-Routers
api_v1_router.include_router(curriculum_router)
api_v1_router.include_router(people_router)
api_v1_router.include_router(offerings_router)

# Mount Milestone 8 Facilities, Timetables & Occurrences Sub-Routers
api_v1_router.include_router(facilities_router)
api_v1_router.include_router(scheduling_router)

# Mount Milestone 9 Attendance Core Engine Sub-Routers
api_v1_router.include_router(attendance_router)
api_v1_router.include_router(student_attendance_router)

# Mount Milestone 13 Student Device Registration & Primary Device Trust Sub-Router
api_v1_router.include_router(devices_router)

# Mount Milestone 14 Campus Presence & Anti-Cheat Hardening Sub-Router
api_v1_router.include_router(security_router)

# Mount Milestone 15 Attendance Operations, Corrections, Excuses & Leave Sub-Router
api_v1_router.include_router(attendance_operations_router)
