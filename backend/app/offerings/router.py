"""API router for Course Offerings, Lecturer Assignments, and Student Enrollments."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_active_user
from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.common.schemas import StandardResponse
from backend.app.core.constants import EnrollmentStatus, OfferingStatus
from backend.app.core.database import get_db_session
from backend.app.core.exceptions import DomainException, NotFoundException
from backend.app.models.lecturer import Lecturer
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.offerings.schemas import (
    BatchEnrollmentRequest,
    CourseOfferingCreateRequest,
    CourseOfferingDetailResponse,
    CourseOfferingResponse,
    CourseOfferingUpdateRequest,
    EnrollmentCreateRequest,
    EnrollmentResponse,
    LecturerAssignmentCreateRequest,
    LecturerAssignmentResponse,
    RosterItemResponse,
    StudentEnrollmentDetailResponse,
)
from backend.app.offerings.service import OfferingService
from backend.app.rbac.dependencies import require_permission
from backend.app.rbac.service import RbacService

router = APIRouter(tags=["Course Offerings & Rosters"])


# ==========================================
# Course Offering Endpoints
# ==========================================


@router.post(
    "/course-offerings",
    response_model=StandardResponse[CourseOfferingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Schedule course offering",
)
async def create_course_offering(
    payload: CourseOfferingCreateRequest,
    current_user: Annotated[
        User, Depends(require_permission("course_offerings.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CourseOfferingResponse]:
    """Create a new semester course offering."""
    if payload.academic_unit_id is not None:
        has_unit_perm = await RbacService.has_academic_unit_permission(
            db=db,
            user_id=current_user.id,
            permission_code="course_offerings.manage",
            university_id=current_user.university_id,
            target_unit_id=payload.academic_unit_id,
        )
        if not has_unit_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message="You lack permission to manage offerings for this academic unit.",
                status_code=403,
            )

    offering = await OfferingService.create_offering(
        db=db,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=CourseOfferingResponse.model_validate(offering),
        meta={"message": "Course offering scheduled successfully."},
    )


@router.get(
    "/course-offerings",
    response_model=StandardResponse[PaginatedResponse[CourseOfferingResponse]],
    summary="List course offerings",
)
async def list_course_offerings(
    current_user: Annotated[
        User, Depends(require_permission("course_offerings.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    pagination: Annotated[PaginationParams, Depends()],
    semester_id: Annotated[uuid.UUID | None, Query(description="Filter by semester")] = None,
    course_id: Annotated[uuid.UUID | None, Query(description="Filter by course")] = None,
    academic_unit_id: Annotated[uuid.UUID | None, Query(description="Filter by unit")] = None,
    lecturer_id: Annotated[
        uuid.UUID | None, Query(description="Filter by assigned lecturer")
    ] = None,
    status_filter: Annotated[OfferingStatus | None, Query(alias="status")] = None,
) -> StandardResponse[PaginatedResponse[CourseOfferingResponse]]:
    """List course offerings with filtering and scope restriction."""
    accessible_unit_ids = await RbacService.get_accessible_academic_unit_ids(
        db=db,
        user_id=current_user.id,
        permission_code="course_offerings.read",
        university_id=current_user.university_id,
    )

    result = await OfferingService.list_offerings(
        db=db,
        university_id=current_user.university_id,
        pagination=pagination,
        semester_id=semester_id,
        course_id=course_id,
        academic_unit_id=academic_unit_id,
        lecturer_id=lecturer_id,
        accessible_unit_ids=accessible_unit_ids,
        status=status_filter,
    )
    return StandardResponse(data=result)


@router.get(
    "/course-offerings/{offering_id}",
    response_model=StandardResponse[CourseOfferingDetailResponse],
    summary="Get course offering details",
)
async def get_course_offering(
    offering_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("course_offerings.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CourseOfferingDetailResponse]:
    """Retrieve detailed course offering information with assigned instructors."""
    offering = await OfferingService.get_offering(
        db=db,
        university_id=current_user.university_id,
        offering_id=offering_id,
    )
    return StandardResponse(data=offering)


@router.patch(
    "/course-offerings/{offering_id}",
    response_model=StandardResponse[CourseOfferingResponse],
    summary="Update course offering",
)
async def update_course_offering(
    offering_id: uuid.UUID,
    payload: CourseOfferingUpdateRequest,
    current_user: Annotated[
        User, Depends(require_permission("course_offerings.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CourseOfferingResponse]:
    """Update course offering properties."""
    if payload.academic_unit_id is not None:
        has_unit_perm = await RbacService.has_academic_unit_permission(
            db=db,
            user_id=current_user.id,
            permission_code="course_offerings.manage",
            university_id=current_user.university_id,
            target_unit_id=payload.academic_unit_id,
        )
        if not has_unit_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message="You lack permission to manage offerings for this academic unit.",
                status_code=403,
            )

    updated = await OfferingService.update_offering(
        db=db,
        university_id=current_user.university_id,
        offering_id=offering_id,
        payload=payload,
    )
    return StandardResponse(
        data=CourseOfferingResponse.model_validate(updated),
        meta={"message": "Course offering updated successfully."},
    )


# ==========================================
# Lecturer Assignment Endpoints
# ==========================================


@router.post(
    "/course-offerings/{offering_id}/lecturers",
    response_model=StandardResponse[LecturerAssignmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Assign instructor to course offering",
)
async def assign_lecturer(
    offering_id: uuid.UUID,
    payload: LecturerAssignmentCreateRequest,
    current_user: Annotated[
        User, Depends(require_permission("course_offerings.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[LecturerAssignmentResponse]:
    """Assign an instructor to a course offering."""
    assignment = await OfferingService.assign_lecturer(
        db=db,
        university_id=current_user.university_id,
        offering_id=offering_id,
        payload=payload,
    )
    return StandardResponse(
        data=LecturerAssignmentResponse.model_validate(assignment),
        meta={"message": "Instructor assigned successfully."},
    )


@router.delete(
    "/course-offerings/{offering_id}/lecturers/{lecturer_id}",
    response_model=StandardResponse[None],
    summary="Remove instructor from course offering",
)
async def remove_lecturer(
    offering_id: uuid.UUID,
    lecturer_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("course_offerings.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[None]:
    """Remove an assigned instructor from a course offering."""
    await OfferingService.remove_lecturer(
        db=db,
        university_id=current_user.university_id,
        offering_id=offering_id,
        lecturer_id=lecturer_id,
    )
    return StandardResponse(
        data=None,
        meta={"message": "Instructor removed from course offering."},
    )


# ==========================================
# Enrollment & Roster Endpoints
# ==========================================


@router.post(
    "/course-offerings/{offering_id}/enrollments",
    response_model=StandardResponse[EnrollmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Enroll student in course offering",
)
async def enroll_student(
    offering_id: uuid.UUID,
    payload: EnrollmentCreateRequest,
    current_user: Annotated[
        User, Depends(require_permission("enrollments.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[EnrollmentResponse]:
    """Enroll a student into a course offering."""
    enrollment = await OfferingService.enroll_student(
        db=db,
        university_id=current_user.university_id,
        offering_id=offering_id,
        student_id=payload.student_id,
    )
    return StandardResponse(
        data=EnrollmentResponse.model_validate(enrollment),
        meta={"message": "Student enrolled successfully."},
    )


@router.post(
    "/course-offerings/{offering_id}/enrollments/batch",
    response_model=StandardResponse[list[EnrollmentResponse]],
    status_code=status.HTTP_201_CREATED,
    summary="Batch enroll students",
)
async def batch_enroll_students(
    offering_id: uuid.UUID,
    payload: BatchEnrollmentRequest,
    current_user: Annotated[
        User, Depends(require_permission("enrollments.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[list[EnrollmentResponse]]:
    """Batch enroll multiple students into a course offering."""
    enrollments = await OfferingService.batch_enroll(
        db=db,
        university_id=current_user.university_id,
        offering_id=offering_id,
        payload=payload,
    )
    return StandardResponse(
        data=[EnrollmentResponse.model_validate(e) for e in enrollments],
        meta={"message": f"Successfully enrolled {len(enrollments)} students."},
    )


@router.get(
    "/course-offerings/{offering_id}/enrollments",
    response_model=StandardResponse[PaginatedResponse[RosterItemResponse]],
    summary="Get course offering class roster",
)
async def get_roster(
    offering_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("enrollments.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    pagination: Annotated[PaginationParams, Depends()],
    status_filter: Annotated[EnrollmentStatus | None, Query(alias="status")] = None,
) -> StandardResponse[PaginatedResponse[RosterItemResponse]]:
    """Retrieve the class roster of students for a course offering."""
    roster = await OfferingService.get_roster(
        db=db,
        university_id=current_user.university_id,
        offering_id=offering_id,
        pagination=pagination,
        status=status_filter,
    )
    return StandardResponse(data=roster)


@router.post(
    "/course-offerings/{offering_id}/enrollments/{student_id}/drop",
    response_model=StandardResponse[EnrollmentResponse],
    summary="Drop student enrollment",
)
@router.delete(
    "/course-offerings/{offering_id}/enrollments/{student_id}",
    response_model=StandardResponse[EnrollmentResponse],
    summary="Drop student enrollment (DELETE alias)",
)
async def drop_student_enrollment(
    offering_id: uuid.UUID,
    student_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("enrollments.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[EnrollmentResponse]:
    """Drop student enrollment preserving the record and timestamps."""
    enrollment = await OfferingService.drop_enrollment(
        db=db,
        university_id=current_user.university_id,
        offering_id=offering_id,
        student_id=student_id,
    )
    return StandardResponse(
        data=EnrollmentResponse.model_validate(enrollment),
        meta={"message": "Enrollment dropped successfully."},
    )


# ==========================================
# Personal Offerings & Enrollments Endpoints
# ==========================================


@router.get(
    "/students/me/enrollments",
    response_model=StandardResponse[list[StudentEnrollmentDetailResponse]],
    summary="Get current user's enrolled courses",
)
async def get_my_enrollments(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[list[StudentEnrollmentDetailResponse]]:
    """Retrieve all course offerings the current student is enrolled in."""
    from sqlalchemy import select

    stmt = select(Student).where(
        Student.university_id == current_user.university_id,
        Student.user_id == current_user.id,
    )
    student = (await db.execute(stmt)).scalar_one_or_none()
    if not student:
        raise NotFoundException("Student", current_user.id)

    enrollments = await OfferingService.get_student_enrollments(
        db=db,
        university_id=current_user.university_id,
        student_id=student.id,
    )
    return StandardResponse(data=enrollments)


@router.get(
    "/lecturers/me/offerings",
    response_model=StandardResponse[PaginatedResponse[CourseOfferingResponse]],
    summary="Get current lecturer's assigned course offerings",
)
async def get_my_offerings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    pagination: Annotated[PaginationParams, Depends()],
    semester_id: Annotated[uuid.UUID | None, Query(description="Filter by semester")] = None,
) -> StandardResponse[PaginatedResponse[CourseOfferingResponse]]:
    """Retrieve all course offerings assigned to the current instructor."""
    from sqlalchemy import select

    stmt = select(Lecturer).where(
        Lecturer.university_id == current_user.university_id,
        Lecturer.user_id == current_user.id,
    )
    lecturer = (await db.execute(stmt)).scalar_one_or_none()
    if not lecturer:
        raise NotFoundException("Lecturer", current_user.id)

    result = await OfferingService.list_offerings(
        db=db,
        university_id=current_user.university_id,
        pagination=pagination,
        semester_id=semester_id,
        lecturer_id=lecturer.id,
    )
    return StandardResponse(data=result)
