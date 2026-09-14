"""API router for recurring timetables, conflict engine, and concrete class occurrences."""

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.auth.dependencies import get_current_user
from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.common.schemas import StandardResponse
from backend.app.core.constants import ClassOccurrenceStatus, TimetableStatus
from backend.app.core.database import get_db_session
from backend.app.core.exceptions import DomainException, NotFoundException
from backend.app.models.course_offering import CourseOffering
from backend.app.models.timetable import Timetable
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_permission
from backend.app.rbac.service import RbacService
from backend.app.scheduling.schemas import (
    ClassOccurrenceDetailResponse,
    OccurrenceCancelRequest,
    OccurrenceGenerationResponse,
    OccurrenceRescheduleRequest,
    TimetableCreateRequest,
    TimetableDetailResponse,
    TimetableUpdateRequest,
)
from backend.app.scheduling.service import SchedulingService

router = APIRouter(tags=["Timetables & Class Occurrences"])


# ==========================================
# Timetable Recurring Rules Endpoints
# ==========================================


@router.post(
    "/timetables",
    response_model=StandardResponse[TimetableDetailResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create recurring timetable rule",
)
async def create_timetable(
    payload: TimetableCreateRequest,
    current_user: Annotated[
        User, Depends(require_permission("timetables.create", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[TimetableDetailResponse]:
    """Define a new weekly timetable rule with multi-resource conflict checking."""
    # Scoped authorization check based on CourseOffering academic unit
    off_stmt = select(CourseOffering).where(
        CourseOffering.id == payload.course_offering_id,
        CourseOffering.university_id == current_user.university_id,
    )
    o_res = await db.execute(off_stmt)
    offering = o_res.scalar_one_or_none()
    if not offering:
        raise NotFoundException("CourseOffering", payload.course_offering_id)

    if offering.academic_unit_id:
        has_perm = await RbacService.has_academic_unit_permission(
            db=db,
            user_id=current_user.id,
            permission_code="timetables.create",
            university_id=current_user.university_id,
            target_unit_id=offering.academic_unit_id,
        )
        if not has_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message="You lack permission to create timetables for this academic unit.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

    timetable = await SchedulingService.create_timetable_rule(
        db=db,
        university_id=current_user.university_id,
        payload=payload,
    )
    detail = await SchedulingService.get_timetable_rule(
        db, timetable.id, current_user.university_id
    )
    return StandardResponse(
        data=detail,
        meta={"message": "Timetable rule created successfully."},
    )


@router.get(
    "/timetables",
    response_model=StandardResponse[PaginatedResponse[TimetableDetailResponse]],
    summary="List recurring timetable rules",
)
async def list_timetables(
    current_user: Annotated[
        User, Depends(require_permission("timetables.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    semester_id: uuid.UUID | None = None,
    course_offering_id: uuid.UUID | None = None,
    academic_unit_id: uuid.UUID | None = None,
    room_id: uuid.UUID | None = None,
    lecturer_id: uuid.UUID | None = None,
    section_id: uuid.UUID | None = None,
    weekday: int | None = Query(None, ge=1, le=7),
    status: TimetableStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> StandardResponse[PaginatedResponse[TimetableDetailResponse]]:
    """List paginated weekly timetable rules with filters."""
    pagination = PaginationParams(page=page, page_size=page_size)
    paginated = await SchedulingService.list_timetables(
        db=db,
        university_id=current_user.university_id,
        pagination=pagination,
        semester_id=semester_id,
        course_offering_id=course_offering_id,
        academic_unit_id=academic_unit_id,
        room_id=room_id,
        lecturer_id=lecturer_id,
        section_id=section_id,
        weekday=weekday,
        status=status,
    )
    return StandardResponse(data=paginated)


@router.get(
    "/timetables/{id}",
    response_model=StandardResponse[TimetableDetailResponse],
    summary="Get timetable rule details",
)
async def get_timetable(
    id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("timetables.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[TimetableDetailResponse]:
    """Retrieve detailed recurring timetable schedule rule by ID."""
    detail = await SchedulingService.get_timetable_rule(
        db=db,
        timetable_id=id,
        university_id=current_user.university_id,
    )
    return StandardResponse(data=detail)


@router.patch(
    "/timetables/{id}",
    response_model=StandardResponse[TimetableDetailResponse],
    summary="Update timetable rule",
)
async def update_timetable(
    id: uuid.UUID,
    payload: TimetableUpdateRequest,
    current_user: Annotated[
        User, Depends(require_permission("timetables.update", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[TimetableDetailResponse]:
    """Update timetable attributes with conflict validation."""
    # Check current rule and academic unit scoping
    stmt = (
        select(Timetable)
        .options(selectinload(Timetable.course_offering))
        .where(
            Timetable.id == id,
            Timetable.university_id == current_user.university_id,
        )
    )
    res = await db.execute(stmt)
    tt = res.scalar_one_or_none()
    if not tt:
        raise NotFoundException("Timetable", id)

    if tt.course_offering.academic_unit_id:
        has_perm = await RbacService.has_academic_unit_permission(
            db=db,
            user_id=current_user.id,
            permission_code="timetables.update",
            university_id=current_user.university_id,
            target_unit_id=tt.course_offering.academic_unit_id,
        )
        if not has_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message="You lack permission to update timetables for this academic unit.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

    detail = await SchedulingService.update_timetable_rule(
        db=db,
        timetable_id=id,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=detail,
        meta={"message": "Timetable rule updated successfully."},
    )


@router.post(
    "/timetables/{id}/activate",
    response_model=StandardResponse[TimetableDetailResponse],
    summary="Activate timetable rule",
)
async def activate_timetable(
    id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("timetables.update", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[TimetableDetailResponse]:
    """Activate a timetable rule."""
    detail = await SchedulingService.set_timetable_status(
        db=db,
        timetable_id=id,
        university_id=current_user.university_id,
        status=TimetableStatus.ACTIVE,
    )
    return StandardResponse(
        data=detail,
        meta={"message": "Timetable rule activated successfully."},
    )


@router.post(
    "/timetables/{id}/deactivate",
    response_model=StandardResponse[TimetableDetailResponse],
    summary="Deactivate timetable rule",
)
async def deactivate_timetable(
    id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("timetables.deactivate", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[TimetableDetailResponse]:
    """Deactivate timetable rule without deleting historical occurrences."""
    detail = await SchedulingService.set_timetable_status(
        db=db,
        timetable_id=id,
        university_id=current_user.university_id,
        status=TimetableStatus.INACTIVE,
    )
    return StandardResponse(
        data=detail,
        meta={"message": "Timetable rule deactivated successfully."},
    )


@router.post(
    "/timetables/{id}/generate-occurrences",
    response_model=StandardResponse[OccurrenceGenerationResponse],
    summary="Generate concrete class occurrences for timetable rule",
)
async def generate_timetable_occurrences(
    id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("timetables.generate_occurrences", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[OccurrenceGenerationResponse]:
    """Expand weekly timetable rule into concrete calendar ClassOccurrence records."""
    report = await SchedulingService.generate_occurrences_for_timetable(
        db=db,
        timetable_id=id,
        university_id=current_user.university_id,
    )
    return StandardResponse(
        data=report,
        meta={"message": report.message},
    )


@router.post(
    "/semesters/{id}/generate-class-occurrences",
    response_model=StandardResponse[OccurrenceGenerationResponse],
    summary="Bulk generate concrete class occurrences for a semester",
)
async def generate_semester_occurrences(
    id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("timetables.generate_occurrences", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[OccurrenceGenerationResponse]:
    """Bulk expand all active timetable rules in a semester into ClassOccurrences."""
    report = await SchedulingService.generate_occurrences_for_semester(
        db=db,
        semester_id=id,
        university_id=current_user.university_id,
    )
    return StandardResponse(
        data=report,
        meta={"message": report.message},
    )


# ==========================================
# ClassOccurrence Endpoints
# ==========================================


@router.get(
    "/class-occurrences",
    response_model=StandardResponse[PaginatedResponse[ClassOccurrenceDetailResponse]],
    summary="List concrete class occurrences",
)
async def list_class_occurrences(
    current_user: Annotated[
        User, Depends(require_permission("class_occurrences.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
    course_offering_id: uuid.UUID | None = None,
    room_id: uuid.UUID | None = None,
    lecturer_id: uuid.UUID | None = None,
    section_id: uuid.UUID | None = None,
    status: ClassOccurrenceStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> StandardResponse[PaginatedResponse[ClassOccurrenceDetailResponse]]:
    """List paginated concrete class meeting dates."""
    pagination = PaginationParams(page=page, page_size=page_size)
    paginated = await SchedulingService.list_class_occurrences(
        db=db,
        university_id=current_user.university_id,
        pagination=pagination,
        from_date=from_date,
        to_date=to_date,
        course_offering_id=course_offering_id,
        room_id=room_id,
        lecturer_id=lecturer_id,
        section_id=section_id,
        status=status,
    )
    return StandardResponse(data=paginated)


@router.get(
    "/class-occurrences/{id}",
    response_model=StandardResponse[ClassOccurrenceDetailResponse],
    summary="Get class occurrence details",
)
async def get_class_occurrence(
    id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("class_occurrences.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[ClassOccurrenceDetailResponse]:
    """Retrieve detailed concrete class meeting by ID."""
    detail = await SchedulingService.get_class_occurrence(
        db=db,
        occurrence_id=id,
        university_id=current_user.university_id,
    )
    return StandardResponse(data=detail)


@router.post(
    "/class-occurrences/{id}/cancel",
    response_model=StandardResponse[ClassOccurrenceDetailResponse],
    summary="Cancel a concrete class occurrence",
)
async def cancel_class_occurrence(
    id: uuid.UUID,
    payload: OccurrenceCancelRequest,
    current_user: Annotated[
        User, Depends(require_permission("class_occurrences.cancel", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[ClassOccurrenceDetailResponse]:
    """Administratively cancel a scheduled class meeting, preserving history."""
    detail = await SchedulingService.cancel_occurrence(
        db=db,
        occurrence_id=id,
        university_id=current_user.university_id,
        reason=payload.reason,
    )
    return StandardResponse(
        data=detail,
        meta={"message": "Class occurrence cancelled successfully."},
    )


@router.post(
    "/class-occurrences/{id}/reschedule",
    response_model=StandardResponse[ClassOccurrenceDetailResponse],
    summary="Reschedule a concrete class occurrence",
)
async def reschedule_class_occurrence(
    id: uuid.UUID,
    payload: OccurrenceRescheduleRequest,
    current_user: Annotated[
        User, Depends(require_permission("class_occurrences.reschedule", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[ClassOccurrenceDetailResponse]:
    """Reschedule a single concrete class occurrence with conflict validation."""
    detail = await SchedulingService.reschedule_occurrence(
        db=db,
        occurrence_id=id,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=detail,
        meta={"message": "Class occurrence rescheduled successfully."},
    )


# ==========================================
# Personal Schedules (Self-Views)
# ==========================================


@router.get(
    "/lecturers/me/class-occurrences",
    response_model=StandardResponse[list[ClassOccurrenceDetailResponse]],
    summary="Get lecturer's personal teaching schedule",
)
async def get_my_lecturer_schedule(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
) -> StandardResponse[list[ClassOccurrenceDetailResponse]]:
    """Retrieve scheduled class meetings for offerings assigned to the logged-in lecturer."""
    schedule = await SchedulingService.get_lecturer_schedule(
        db=db,
        user_id=current_user.id,
        university_id=current_user.university_id,
        from_date=from_date,
        to_date=to_date,
    )
    return StandardResponse(data=schedule)


@router.get(
    "/students/me/class-occurrences",
    response_model=StandardResponse[list[ClassOccurrenceDetailResponse]],
    summary="Get student's personal class schedule",
)
async def get_my_student_schedule(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
) -> StandardResponse[list[ClassOccurrenceDetailResponse]]:
    """Retrieve scheduled class meetings for offerings actively enrolled
    by the logged-in student.
    """
    schedule = await SchedulingService.get_student_schedule(
        db=db,
        user_id=current_user.id,
        university_id=current_user.university_id,
        from_date=from_date,
        to_date=to_date,
    )
    return StandardResponse(data=schedule)
