"""Academic calendar API routers for academic years and semesters."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.calendar.schemas import (
    AcademicYearCreateRequest,
    AcademicYearDetailResponse,
    AcademicYearResponse,
    AcademicYearUpdateRequest,
    SemesterCreateRequest,
    SemesterResponse,
    SemesterUpdateRequest,
)
from backend.app.calendar.service import AcademicCalendarService
from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.common.schemas import StandardResponse
from backend.app.core.database import get_db_session
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_permission

academic_years_router = APIRouter(prefix="/academic-years", tags=["Academic Calendar - Years"])
semesters_router = APIRouter(prefix="/semesters", tags=["Academic Calendar - Semesters"])


# =============================================================================
# Academic Years Endpoints
# =============================================================================


@academic_years_router.post(
    "",
    response_model=StandardResponse[AcademicYearResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create academic year",
)
async def create_academic_year(
    payload: AcademicYearCreateRequest,
    current_user: Annotated[User, Depends(require_permission("academic_years.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AcademicYearResponse]:
    year = await AcademicCalendarService.create_academic_year(
        db=db,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=AcademicYearResponse.model_validate(year),
        meta={"message": "Academic year created successfully."},
    )


@academic_years_router.get(
    "",
    response_model=PaginatedResponse[AcademicYearResponse],
    summary="List academic years",
)
async def list_academic_years(
    current_user: Annotated[User, Depends(require_permission("academic_years.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page_params: Annotated[PaginationParams, Depends()],
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    is_current: Annotated[bool | None, Query(description="Filter by current flag")] = None,
) -> PaginatedResponse[AcademicYearResponse]:
    return await AcademicCalendarService.list_academic_years(
        db=db,
        university_id=current_user.university_id,
        page_params=page_params,
        status=status,
        is_current=is_current,
    )


@academic_years_router.get(
    "/current",
    response_model=StandardResponse[AcademicYearResponse | None],
    summary="Get current academic year",
)
async def get_current_academic_year(
    current_user: Annotated[User, Depends(require_permission("academic_years.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AcademicYearResponse | None]:
    year = await AcademicCalendarService.get_current_academic_year(
        db=db,
        university_id=current_user.university_id,
    )
    return StandardResponse(data=AcademicYearResponse.model_validate(year) if year else None)


@academic_years_router.get(
    "/{year_id}",
    response_model=StandardResponse[AcademicYearDetailResponse],
    summary="Get academic year details",
)
async def get_academic_year(
    year_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("academic_years.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AcademicYearDetailResponse]:
    detail = await AcademicCalendarService.get_academic_year_by_id(
        db=db,
        university_id=current_user.university_id,
        year_id=year_id,
    )
    return StandardResponse(data=detail)


@academic_years_router.patch(
    "/{year_id}",
    response_model=StandardResponse[AcademicYearResponse],
    summary="Update academic year",
)
async def update_academic_year(
    year_id: uuid.UUID,
    payload: AcademicYearUpdateRequest,
    current_user: Annotated[User, Depends(require_permission("academic_years.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AcademicYearResponse]:
    year = await AcademicCalendarService.update_academic_year(
        db=db,
        university_id=current_user.university_id,
        year_id=year_id,
        payload=payload,
    )
    return StandardResponse(
        data=AcademicYearResponse.model_validate(year),
        meta={"message": "Academic year updated successfully."},
    )


@academic_years_router.post(
    "/{year_id}/set-current",
    response_model=StandardResponse[AcademicYearResponse],
    summary="Designate academic year as current active year",
)
async def set_current_academic_year(
    year_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("academic_years.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AcademicYearResponse]:
    year = await AcademicCalendarService.set_current_academic_year(
        db=db,
        university_id=current_user.university_id,
        year_id=year_id,
    )
    return StandardResponse(
        data=AcademicYearResponse.model_validate(year),
        meta={"message": "Academic year set as current successfully."},
    )


# =============================================================================
# Semesters Endpoints
# =============================================================================


@semesters_router.post(
    "",
    response_model=StandardResponse[SemesterResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create semester calendar session",
)
async def create_semester(
    payload: SemesterCreateRequest,
    current_user: Annotated[User, Depends(require_permission("semesters.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[SemesterResponse]:
    semester = await AcademicCalendarService.create_semester(
        db=db,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=SemesterResponse.model_validate(semester),
        meta={"message": "Semester created successfully."},
    )


@semesters_router.get(
    "",
    response_model=PaginatedResponse[SemesterResponse],
    summary="List semesters",
)
async def list_semesters(
    current_user: Annotated[User, Depends(require_permission("semesters.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page_params: Annotated[PaginationParams, Depends()],
    academic_year_id: Annotated[uuid.UUID | None, Query(description="Filter by year ID")] = None,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    is_current: Annotated[bool | None, Query(description="Filter by current flag")] = None,
) -> PaginatedResponse[SemesterResponse]:
    return await AcademicCalendarService.list_semesters(
        db=db,
        university_id=current_user.university_id,
        page_params=page_params,
        academic_year_id=academic_year_id,
        status=status,
        is_current=is_current,
    )


@semesters_router.get(
    "/current",
    response_model=StandardResponse[SemesterResponse | None],
    summary="Get current active semester",
)
async def get_current_semester(
    current_user: Annotated[User, Depends(require_permission("semesters.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[SemesterResponse | None]:
    semester = await AcademicCalendarService.get_current_semester(
        db=db,
        university_id=current_user.university_id,
    )
    return StandardResponse(data=SemesterResponse.model_validate(semester) if semester else None)


@semesters_router.get(
    "/{semester_id}",
    response_model=StandardResponse[SemesterResponse],
    summary="Get semester details",
)
async def get_semester(
    semester_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("semesters.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[SemesterResponse]:
    semester = await AcademicCalendarService.get_semester_by_id(
        db=db,
        university_id=current_user.university_id,
        semester_id=semester_id,
    )
    return StandardResponse(data=SemesterResponse.model_validate(semester))


@semesters_router.patch(
    "/{semester_id}",
    response_model=StandardResponse[SemesterResponse],
    summary="Update semester",
)
async def update_semester(
    semester_id: uuid.UUID,
    payload: SemesterUpdateRequest,
    current_user: Annotated[User, Depends(require_permission("semesters.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[SemesterResponse]:
    semester = await AcademicCalendarService.update_semester(
        db=db,
        university_id=current_user.university_id,
        semester_id=semester_id,
        payload=payload,
    )
    return StandardResponse(
        data=SemesterResponse.model_validate(semester),
        meta={"message": "Semester updated successfully."},
    )


@semesters_router.post(
    "/{semester_id}/set-current",
    response_model=StandardResponse[SemesterResponse],
    summary="Designate semester as current active session",
)
async def set_current_semester(
    semester_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("semesters.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[SemesterResponse]:
    semester = await AcademicCalendarService.set_current_semester(
        db=db,
        university_id=current_user.university_id,
        semester_id=semester_id,
    )
    return StandardResponse(
        data=SemesterResponse.model_validate(semester),
        meta={"message": "Semester set as current successfully."},
    )
