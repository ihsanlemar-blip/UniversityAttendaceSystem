"""Academic unit management API router."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.academic.schemas import (
    AcademicUnitCreateRequest,
    AcademicUnitDetailResponse,
    AcademicUnitMoveRequest,
    AcademicUnitResponse,
    AcademicUnitTreeNodeResponse,
    AcademicUnitUpdateRequest,
)
from backend.app.academic.service import AcademicUnitService
from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.common.schemas import StandardResponse
from backend.app.core.database import get_db_session
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_academic_unit_permission, require_permission

router = APIRouter(prefix="/academic-units", tags=["Academic Hierarchy"])


@router.post(
    "",
    response_model=StandardResponse[AcademicUnitResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create academic unit",
    description="Register a new academic unit (Faculty, Department, Program) in the university.",
)
async def create_academic_unit(
    payload: AcademicUnitCreateRequest,
    current_user: Annotated[User, Depends(require_permission("academic_units.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AcademicUnitResponse]:
    unit = await AcademicUnitService.create_unit(
        db=db,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=AcademicUnitResponse.model_validate(unit),
        meta={"message": "Academic unit created successfully."},
    )


@router.get(
    "/tree",
    response_model=StandardResponse[list[AcademicUnitTreeNodeResponse]],
    summary="Get academic unit tree",
    description="Returns the full organizational tree or a subtree without N+1 query overhead.",
)
async def get_academic_unit_tree(
    current_user: Annotated[User, Depends(require_permission("academic_units.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    root_id: Annotated[
        uuid.UUID | None, Query(description="Filter tree from specific root")
    ] = None,
) -> StandardResponse[list[AcademicUnitTreeNodeResponse]]:
    tree = await AcademicUnitService.get_unit_tree(
        db=db,
        university_id=current_user.university_id,
        root_id=root_id,
    )
    return StandardResponse(data=tree)


@router.get(
    "",
    response_model=PaginatedResponse[AcademicUnitResponse],
    summary="List academic units",
    description="List academic units with optional filtering by parent, type, or status.",
)
async def list_academic_units(
    current_user: Annotated[User, Depends(require_permission("academic_units.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page_params: Annotated[PaginationParams, Depends()],
    parent_id: Annotated[uuid.UUID | None, Query(description="Filter by parent ID")] = None,
    root_only: Annotated[
        bool, Query(description="Filter only root units (parent_id IS NULL)")
    ] = False,
    unit_type: Annotated[str | None, Query(description="Filter by unit type")] = None,
    status: Annotated[str | None, Query(description="Filter by unit status")] = None,
) -> PaginatedResponse[AcademicUnitResponse]:
    return await AcademicUnitService.list_units(
        db=db,
        university_id=current_user.university_id,
        page_params=page_params,
        parent_id=parent_id,
        is_root_only=root_only,
        unit_type=unit_type,
        status=status,
    )


@router.get(
    "/{unit_id}",
    response_model=StandardResponse[AcademicUnitDetailResponse],
    summary="Get academic unit details",
    description="Retrieve academic unit metadata, parent info, child count, and ancestor path.",
)
async def get_academic_unit(
    unit_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("academic_units.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AcademicUnitDetailResponse]:
    detail = await AcademicUnitService.get_unit_by_id(
        db=db,
        university_id=current_user.university_id,
        unit_id=unit_id,
    )
    return StandardResponse(data=detail)


@router.patch(
    "/{unit_id}",
    response_model=StandardResponse[AcademicUnitResponse],
    summary="Update academic unit",
    description="Update academic unit name, code, short_name, or sort ordering.",
)
async def update_academic_unit(
    unit_id: uuid.UUID,
    payload: AcademicUnitUpdateRequest,
    current_user: Annotated[
        User, Depends(require_academic_unit_permission("academic_units.manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AcademicUnitResponse]:
    unit = await AcademicUnitService.update_unit(
        db=db,
        university_id=current_user.university_id,
        unit_id=unit_id,
        payload=payload,
    )
    return StandardResponse(
        data=AcademicUnitResponse.model_validate(unit),
        meta={"message": "Academic unit updated successfully."},
    )


@router.post(
    "/{unit_id}/move",
    response_model=StandardResponse[AcademicUnitResponse],
    summary="Reparent academic unit",
    description="Move unit to a new parent or to root level with cycle prevention.",
)
async def move_academic_unit(
    unit_id: uuid.UUID,
    payload: AcademicUnitMoveRequest,
    current_user: Annotated[
        User, Depends(require_academic_unit_permission("academic_units.manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AcademicUnitResponse]:
    unit = await AcademicUnitService.move_unit(
        db=db,
        university_id=current_user.university_id,
        unit_id=unit_id,
        payload=payload,
    )
    return StandardResponse(
        data=AcademicUnitResponse.model_validate(unit),
        meta={"message": "Academic unit moved successfully."},
    )


@router.post(
    "/{unit_id}/deactivate",
    response_model=StandardResponse[AcademicUnitResponse],
    summary="Deactivate academic unit",
    description="Soft-deactivate an academic unit (blocked if active children exist).",
)
async def deactivate_academic_unit(
    unit_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_academic_unit_permission("academic_units.manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AcademicUnitResponse]:
    unit = await AcademicUnitService.deactivate_unit(
        db=db,
        university_id=current_user.university_id,
        unit_id=unit_id,
    )
    return StandardResponse(
        data=AcademicUnitResponse.model_validate(unit),
        meta={"message": "Academic unit deactivated successfully."},
    )


@router.post(
    "/{unit_id}/activate",
    response_model=StandardResponse[AcademicUnitResponse],
    summary="Reactivate academic unit",
    description="Reactivate an academic unit (requires parent to be active).",
)
async def activate_academic_unit(
    unit_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_academic_unit_permission("academic_units.manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AcademicUnitResponse]:
    unit = await AcademicUnitService.activate_unit(
        db=db,
        university_id=current_user.university_id,
        unit_id=unit_id,
    )
    return StandardResponse(
        data=AcademicUnitResponse.model_validate(unit),
        meta={"message": "Academic unit activated successfully."},
    )
