"""API router for master course catalog and student sections."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.common.schemas import StandardResponse
from backend.app.core.constants import RecordStatus
from backend.app.core.database import get_db_session
from backend.app.core.exceptions import DomainException
from backend.app.curriculum.schemas import (
    CourseCreateRequest,
    CourseDetailResponse,
    CourseResponse,
    CourseUpdateRequest,
    SectionCreateRequest,
    SectionDetailResponse,
    SectionResponse,
    SectionUpdateRequest,
)
from backend.app.curriculum.service import CurriculumService
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_permission
from backend.app.rbac.service import RbacService

router = APIRouter(tags=["Curriculum & Cohorts"])


# ==========================================
# Course Endpoints
# ==========================================


@router.post(
    "/courses",
    response_model=StandardResponse[CourseResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create course catalog item",
)
async def create_course(
    payload: CourseCreateRequest,
    current_user: Annotated[User, Depends(require_permission("courses.manage", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CourseResponse]:
    """Create a new course catalog definition."""
    if payload.academic_unit_id is not None:
        has_unit_perm = await RbacService.has_academic_unit_permission(
            db=db,
            user_id=current_user.id,
            permission_code="courses.manage",
            university_id=current_user.university_id,
            target_unit_id=payload.academic_unit_id,
        )
        if not has_unit_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message="You lack permission to manage courses for this academic unit.",
                status_code=403,
            )
    else:
        has_uni_perm = await RbacService.has_permission(
            db=db,
            user_id=current_user.id,
            permission_code="courses.manage",
            university_id=current_user.university_id,
            allow_scoped=False,
        )
        if not has_uni_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message=(
                    "University-scoped permission required to create courses without academic unit."
                ),
                status_code=403,
            )

    course = await CurriculumService.create_course(
        db=db,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=CourseResponse.model_validate(course),
        meta={"message": "Course created successfully."},
    )


@router.get(
    "/courses",
    response_model=StandardResponse[PaginatedResponse[CourseResponse]],
    summary="List courses with pagination and scope filtering",
)
async def list_courses(
    current_user: Annotated[User, Depends(require_permission("courses.read", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    pagination: Annotated[PaginationParams, Depends()],
    academic_unit_id: Annotated[uuid.UUID | None, Query(description="Filter by unit")] = None,
    status_filter: Annotated[RecordStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(description="Search code or name")] = None,
) -> StandardResponse[PaginatedResponse[CourseResponse]]:
    """List catalog courses accessible to the authenticated user."""
    accessible_unit_ids = await RbacService.get_accessible_academic_unit_ids(
        db=db,
        user_id=current_user.id,
        permission_code="courses.read",
        university_id=current_user.university_id,
    )

    result = await CurriculumService.list_courses(
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
    "/courses/{course_id}",
    response_model=StandardResponse[CourseDetailResponse],
    summary="Get course catalog item details",
)
async def get_course(
    course_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("courses.read", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CourseDetailResponse]:
    """Retrieve detailed course information."""
    course = await CurriculumService.get_course(
        db=db,
        university_id=current_user.university_id,
        course_id=course_id,
    )
    return StandardResponse(data=course)


@router.patch(
    "/courses/{course_id}",
    response_model=StandardResponse[CourseResponse],
    summary="Update course catalog item",
)
async def update_course(
    course_id: uuid.UUID,
    payload: CourseUpdateRequest,
    current_user: Annotated[User, Depends(require_permission("courses.manage", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CourseResponse]:
    """Update course attributes."""
    if payload.academic_unit_id is not None:
        has_unit_perm = await RbacService.has_academic_unit_permission(
            db=db,
            user_id=current_user.id,
            permission_code="courses.manage",
            university_id=current_user.university_id,
            target_unit_id=payload.academic_unit_id,
        )
        if not has_unit_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message="You lack permission to manage courses for this academic unit.",
                status_code=403,
            )

    updated = await CurriculumService.update_course(
        db=db,
        university_id=current_user.university_id,
        course_id=course_id,
        payload=payload,
    )
    return StandardResponse(
        data=CourseResponse.model_validate(updated),
        meta={"message": "Course updated successfully."},
    )


@router.delete(
    "/courses/{course_id}",
    response_model=StandardResponse[None],
    summary="Delete course catalog item",
)
async def delete_course(
    course_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("courses.manage", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[None]:
    """Delete a course if no course offerings reference it."""
    await CurriculumService.delete_course(
        db=db,
        university_id=current_user.university_id,
        course_id=course_id,
    )
    return StandardResponse(
        data=None,
        meta={"message": "Course deleted successfully."},
    )


# ==========================================
# Section Endpoints
# ==========================================


@router.post(
    "/sections",
    response_model=StandardResponse[SectionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create student section cohort",
)
async def create_section(
    payload: SectionCreateRequest,
    current_user: Annotated[
        User, Depends(require_permission("sections.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[SectionResponse]:
    """Create a new section cohort."""
    if payload.academic_unit_id is not None:
        has_unit_perm = await RbacService.has_academic_unit_permission(
            db=db,
            user_id=current_user.id,
            permission_code="sections.manage",
            university_id=current_user.university_id,
            target_unit_id=payload.academic_unit_id,
        )
        if not has_unit_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message="You lack permission to manage sections for this academic unit.",
                status_code=403,
            )

    section = await CurriculumService.create_section(
        db=db,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=SectionResponse.model_validate(section),
        meta={"message": "Section created successfully."},
    )


@router.get(
    "/sections",
    response_model=StandardResponse[PaginatedResponse[SectionResponse]],
    summary="List student sections",
)
async def list_sections(
    current_user: Annotated[User, Depends(require_permission("sections.read", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    pagination: Annotated[PaginationParams, Depends()],
    semester_id: Annotated[uuid.UUID | None, Query(description="Filter by semester")] = None,
    academic_unit_id: Annotated[uuid.UUID | None, Query(description="Filter by unit")] = None,
    status_filter: Annotated[RecordStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(description="Search section code or name")] = None,
) -> StandardResponse[PaginatedResponse[SectionResponse]]:
    """List sections with pagination and filtering."""
    accessible_unit_ids = await RbacService.get_accessible_academic_unit_ids(
        db=db,
        user_id=current_user.id,
        permission_code="sections.read",
        university_id=current_user.university_id,
    )

    result = await CurriculumService.list_sections(
        db=db,
        university_id=current_user.university_id,
        pagination=pagination,
        semester_id=semester_id,
        academic_unit_id=academic_unit_id,
        accessible_unit_ids=accessible_unit_ids,
        status=status_filter,
        search=search,
    )
    return StandardResponse(data=result)


@router.get(
    "/sections/{section_id}",
    response_model=StandardResponse[SectionDetailResponse],
    summary="Get section details",
)
async def get_section(
    section_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("sections.read", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[SectionDetailResponse]:
    """Retrieve detailed section information."""
    section = await CurriculumService.get_section(
        db=db,
        university_id=current_user.university_id,
        section_id=section_id,
    )
    return StandardResponse(data=section)


@router.patch(
    "/sections/{section_id}",
    response_model=StandardResponse[SectionResponse],
    summary="Update section cohort",
)
async def update_section(
    section_id: uuid.UUID,
    payload: SectionUpdateRequest,
    current_user: Annotated[
        User, Depends(require_permission("sections.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[SectionResponse]:
    """Update section cohort properties."""
    if payload.academic_unit_id is not None:
        has_unit_perm = await RbacService.has_academic_unit_permission(
            db=db,
            user_id=current_user.id,
            permission_code="sections.manage",
            university_id=current_user.university_id,
            target_unit_id=payload.academic_unit_id,
        )
        if not has_unit_perm:
            raise DomainException(
                code="PERMISSION_DENIED",
                message="You lack permission to manage sections for this academic unit.",
                status_code=403,
            )

    updated = await CurriculumService.update_section(
        db=db,
        university_id=current_user.university_id,
        section_id=section_id,
        payload=payload,
    )
    return StandardResponse(
        data=SectionResponse.model_validate(updated),
        meta={"message": "Section updated successfully."},
    )
