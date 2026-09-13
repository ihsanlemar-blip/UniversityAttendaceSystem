"""API router for Student and Lecturer profiles."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_active_user
from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.common.schemas import StandardResponse
from backend.app.core.constants import LecturerStatus, StudentStatus
from backend.app.core.database import get_db_session
from backend.app.core.exceptions import DomainException
from backend.app.models.user import User
from backend.app.people.schemas import (
    LecturerCreateRequest,
    LecturerDetailResponse,
    LecturerResponse,
    LecturerUpdateRequest,
    StudentCreateRequest,
    StudentDetailResponse,
    StudentResponse,
    StudentUpdateRequest,
)
from backend.app.people.service import PeopleService
from backend.app.rbac.dependencies import require_permission
from backend.app.rbac.service import RbacService

router = APIRouter(tags=["People & Profiles"])


# ==========================================
# Student Endpoints
# ==========================================


@router.post(
    "/students",
    response_model=StandardResponse[StudentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create student profile",
)
async def create_student(
    payload: StudentCreateRequest,
    current_user: Annotated[
        User, Depends(require_permission("students.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[StudentResponse]:
    """Create a student profile linked to a User account."""
    if payload.academic_unit_id is not None:
        has_unit_perm = await RbacService.has_academic_unit_permission(
            db=db,
            user_id=current_user.id,
            permission_code="students.manage",
            university_id=current_user.university_id,
            target_unit_id=payload.academic_unit_id,
        )
        if not has_unit_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message="You lack permission to manage students for this academic unit.",
                status_code=403,
            )
    else:
        has_uni_perm = await RbacService.has_permission(
            db=db,
            user_id=current_user.id,
            permission_code="students.manage",
            university_id=current_user.university_id,
            allow_scoped=False,
        )
        if not has_uni_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message=(
                    "University-scoped permission required to manage students without academic"
                    " unit."
                ),
                status_code=403,
            )

    student = await PeopleService.create_student(
        db=db,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=StudentResponse.model_validate(student),
        meta={"message": "Student profile created successfully."},
    )


@router.get(
    "/students",
    response_model=StandardResponse[PaginatedResponse[StudentResponse]],
    summary="List student profiles",
)
async def list_students(
    current_user: Annotated[User, Depends(require_permission("students.read", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    pagination: Annotated[PaginationParams, Depends()],
    academic_unit_id: Annotated[uuid.UUID | None, Query(description="Filter by unit")] = None,
    section_id: Annotated[uuid.UUID | None, Query(description="Filter by section")] = None,
    status_filter: Annotated[StudentStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(description="Search student number, name, email")] = None,
) -> StandardResponse[PaginatedResponse[StudentResponse]]:
    """List students with pagination and scope filtering."""
    accessible_unit_ids = await RbacService.get_accessible_academic_unit_ids(
        db=db,
        user_id=current_user.id,
        permission_code="students.read",
        university_id=current_user.university_id,
    )

    result = await PeopleService.list_students(
        db=db,
        university_id=current_user.university_id,
        pagination=pagination,
        academic_unit_id=academic_unit_id,
        section_id=section_id,
        accessible_unit_ids=accessible_unit_ids,
        status=status_filter,
        search=search,
    )
    return StandardResponse(data=result)


@router.get(
    "/students/me",
    response_model=StandardResponse[StudentDetailResponse],
    summary="Get current user's student profile",
)
async def get_my_student_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[StudentDetailResponse]:
    """Retrieve the student profile of the currently authenticated user."""
    profile = await PeopleService.get_student_by_user_id(
        db=db,
        university_id=current_user.university_id,
        user_id=current_user.id,
    )
    return StandardResponse(data=profile)


@router.get(
    "/students/{student_id}",
    response_model=StandardResponse[StudentDetailResponse],
    summary="Get student profile details",
)
async def get_student(
    student_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("students.read", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[StudentDetailResponse]:
    """Retrieve detailed student profile."""
    profile = await PeopleService.get_student(
        db=db,
        university_id=current_user.university_id,
        student_id=student_id,
    )
    return StandardResponse(data=profile)


@router.patch(
    "/students/{student_id}",
    response_model=StandardResponse[StudentResponse],
    summary="Update student profile",
)
async def update_student(
    student_id: uuid.UUID,
    payload: StudentUpdateRequest,
    current_user: Annotated[
        User, Depends(require_permission("students.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[StudentResponse]:
    """Update student profile attributes."""
    if payload.academic_unit_id is not None:
        has_unit_perm = await RbacService.has_academic_unit_permission(
            db=db,
            user_id=current_user.id,
            permission_code="students.manage",
            university_id=current_user.university_id,
            target_unit_id=payload.academic_unit_id,
        )
        if not has_unit_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message="You lack permission to manage students for this academic unit.",
                status_code=403,
            )

    updated = await PeopleService.update_student(
        db=db,
        university_id=current_user.university_id,
        student_id=student_id,
        payload=payload,
    )
    return StandardResponse(
        data=StudentResponse.model_validate(updated),
        meta={"message": "Student profile updated successfully."},
    )


# ==========================================
# Lecturer Endpoints
# ==========================================


@router.post(
    "/lecturers",
    response_model=StandardResponse[LecturerResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create lecturer profile",
)
async def create_lecturer(
    payload: LecturerCreateRequest,
    current_user: Annotated[
        User, Depends(require_permission("lecturers.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[LecturerResponse]:
    """Create a lecturer profile linked to a User account."""
    if payload.academic_unit_id is not None:
        has_unit_perm = await RbacService.has_academic_unit_permission(
            db=db,
            user_id=current_user.id,
            permission_code="lecturers.manage",
            university_id=current_user.university_id,
            target_unit_id=payload.academic_unit_id,
        )
        if not has_unit_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message="You lack permission to manage lecturers for this academic unit.",
                status_code=403,
            )
    else:
        has_uni_perm = await RbacService.has_permission(
            db=db,
            user_id=current_user.id,
            permission_code="lecturers.manage",
            university_id=current_user.university_id,
            allow_scoped=False,
        )
        if not has_uni_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message=(
                    "University-scoped permission required to manage lecturers without academic"
                    " unit."
                ),
                status_code=403,
            )

    lecturer = await PeopleService.create_lecturer(
        db=db,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=LecturerResponse.model_validate(lecturer),
        meta={"message": "Lecturer profile created successfully."},
    )


@router.get(
    "/lecturers",
    response_model=StandardResponse[PaginatedResponse[LecturerResponse]],
    summary="List lecturer profiles",
)
async def list_lecturers(
    current_user: Annotated[User, Depends(require_permission("lecturers.read", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    pagination: Annotated[PaginationParams, Depends()],
    academic_unit_id: Annotated[uuid.UUID | None, Query(description="Filter by unit")] = None,
    status_filter: Annotated[LecturerStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(description="Search employee code, name, email")] = None,
) -> StandardResponse[PaginatedResponse[LecturerResponse]]:
    """List lecturers with pagination and scope filtering."""
    accessible_unit_ids = await RbacService.get_accessible_academic_unit_ids(
        db=db,
        user_id=current_user.id,
        permission_code="lecturers.read",
        university_id=current_user.university_id,
    )

    result = await PeopleService.list_lecturers(
        db=db,
        university_id=current_user.university_id,
        pagination=pagination,
        academic_unit_id=academic_unit_id,
        accessible_unit_ids=accessible_unit_ids,
        status=status_filter,
        search=search,
    )
    return StandardResponse(data=result)


@router.get(
    "/lecturers/me",
    response_model=StandardResponse[LecturerDetailResponse],
    summary="Get current user's lecturer profile",
)
async def get_my_lecturer_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[LecturerDetailResponse]:
    """Retrieve the lecturer profile of the currently authenticated user."""
    profile = await PeopleService.get_lecturer_by_user_id(
        db=db,
        university_id=current_user.university_id,
        user_id=current_user.id,
    )
    return StandardResponse(data=profile)


@router.get(
    "/lecturers/{lecturer_id}",
    response_model=StandardResponse[LecturerDetailResponse],
    summary="Get lecturer profile details",
)
async def get_lecturer(
    lecturer_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("lecturers.read", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[LecturerDetailResponse]:
    """Retrieve detailed lecturer profile."""
    profile = await PeopleService.get_lecturer(
        db=db,
        university_id=current_user.university_id,
        lecturer_id=lecturer_id,
    )
    return StandardResponse(data=profile)


@router.patch(
    "/lecturers/{lecturer_id}",
    response_model=StandardResponse[LecturerResponse],
    summary="Update lecturer profile",
)
async def update_lecturer(
    lecturer_id: uuid.UUID,
    payload: LecturerUpdateRequest,
    current_user: Annotated[
        User, Depends(require_permission("lecturers.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[LecturerResponse]:
    """Update lecturer profile attributes."""
    if payload.academic_unit_id is not None:
        has_unit_perm = await RbacService.has_academic_unit_permission(
            db=db,
            user_id=current_user.id,
            permission_code="lecturers.manage",
            university_id=current_user.university_id,
            target_unit_id=payload.academic_unit_id,
        )
        if not has_unit_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message="You lack permission to manage lecturers for this academic unit.",
                status_code=403,
            )

    updated = await PeopleService.update_lecturer(
        db=db,
        university_id=current_user.university_id,
        lecturer_id=lecturer_id,
        payload=payload,
    )
    return StandardResponse(
        data=LecturerResponse.model_validate(updated),
        meta={"message": "Lecturer profile updated successfully."},
    )
