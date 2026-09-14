"""API router for campus Building and Room facilities."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.common.schemas import StandardResponse
from backend.app.core.constants import BuildingStatus, RoomStatus
from backend.app.core.database import get_db_session
from backend.app.facilities.schemas import (
    BuildingCreateRequest,
    BuildingResponse,
    BuildingUpdateRequest,
    RoomCreateRequest,
    RoomDetailResponse,
    RoomUpdateRequest,
)
from backend.app.facilities.service import BuildingService, RoomService
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_permission

router = APIRouter(tags=["Facilities & Campus Spaces"])


# ==========================================
# Building Endpoints
# ==========================================


@router.post(
    "/buildings",
    response_model=StandardResponse[BuildingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a campus building",
)
async def create_building(
    payload: BuildingCreateRequest,
    current_user: Annotated[User, Depends(require_permission("buildings.create"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[BuildingResponse]:
    """Create a new campus building definition."""
    building = await BuildingService.create_building(
        db=db,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=BuildingResponse.model_validate(building),
        meta={"message": "Building created successfully."},
    )


@router.get(
    "/buildings",
    response_model=StandardResponse[PaginatedResponse[BuildingResponse]],
    summary="List campus buildings",
)
async def list_buildings(
    current_user: Annotated[User, Depends(require_permission("buildings.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    status: BuildingStatus | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> StandardResponse[PaginatedResponse[BuildingResponse]]:
    """List paginated buildings in the current user's university."""
    pagination = PaginationParams(page=page, page_size=page_size)
    paginated = await BuildingService.list_buildings(
        db=db,
        university_id=current_user.university_id,
        pagination=pagination,
        status=status,
        search=search,
    )
    return StandardResponse(data=paginated)


@router.get(
    "/buildings/{id}",
    response_model=StandardResponse[BuildingResponse],
    summary="Get building details",
)
async def get_building(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("buildings.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[BuildingResponse]:
    """Retrieve building details by ID."""
    building = await BuildingService.get_building(
        db=db,
        building_id=id,
        university_id=current_user.university_id,
    )
    return StandardResponse(data=BuildingResponse.model_validate(building))


@router.patch(
    "/buildings/{id}",
    response_model=StandardResponse[BuildingResponse],
    summary="Update building",
)
async def update_building(
    id: uuid.UUID,
    payload: BuildingUpdateRequest,
    current_user: Annotated[User, Depends(require_permission("buildings.update"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[BuildingResponse]:
    """Update building attributes."""
    building = await BuildingService.update_building(
        db=db,
        building_id=id,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=BuildingResponse.model_validate(building),
        meta={"message": "Building updated successfully."},
    )


@router.post(
    "/buildings/{id}/activate",
    response_model=StandardResponse[BuildingResponse],
    summary="Activate building",
)
async def activate_building(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("buildings.update"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[BuildingResponse]:
    """Activate an inactive campus building."""
    building = await BuildingService.set_building_status(
        db=db,
        building_id=id,
        university_id=current_user.university_id,
        status=BuildingStatus.ACTIVE,
    )
    return StandardResponse(
        data=BuildingResponse.model_validate(building),
        meta={"message": "Building activated successfully."},
    )


@router.post(
    "/buildings/{id}/deactivate",
    response_model=StandardResponse[BuildingResponse],
    summary="Deactivate building",
)
async def deactivate_building(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("buildings.deactivate"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[BuildingResponse]:
    """Deactivate a campus building without deleting room history."""
    building = await BuildingService.set_building_status(
        db=db,
        building_id=id,
        university_id=current_user.university_id,
        status=BuildingStatus.INACTIVE,
    )
    return StandardResponse(
        data=BuildingResponse.model_validate(building),
        meta={"message": "Building deactivated successfully."},
    )


# ==========================================
# Room Endpoints
# ==========================================


@router.post(
    "/rooms",
    response_model=StandardResponse[RoomDetailResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a room facility",
)
async def create_room(
    payload: RoomCreateRequest,
    current_user: Annotated[User, Depends(require_permission("rooms.create"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[RoomDetailResponse]:
    """Register a new room within a campus building."""
    room = await RoomService.create_room(
        db=db,
        university_id=current_user.university_id,
        payload=payload,
    )
    detail = await RoomService.get_room(db, room.id, current_user.university_id)
    return StandardResponse(
        data=detail,
        meta={"message": "Room created successfully."},
    )


@router.get(
    "/rooms",
    response_model=StandardResponse[PaginatedResponse[RoomDetailResponse]],
    summary="List rooms",
)
async def list_rooms(
    current_user: Annotated[User, Depends(require_permission("rooms.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    building_id: uuid.UUID | None = None,
    status: RoomStatus | None = None,
    capacity_min: int | None = Query(None, gt=0),
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> StandardResponse[PaginatedResponse[RoomDetailResponse]]:
    """List paginated rooms in the current user's university."""
    pagination = PaginationParams(page=page, page_size=page_size)
    paginated = await RoomService.list_rooms(
        db=db,
        university_id=current_user.university_id,
        pagination=pagination,
        building_id=building_id,
        status=status,
        capacity_min=capacity_min,
        search=search,
    )
    return StandardResponse(data=paginated)


@router.get(
    "/rooms/{id}",
    response_model=StandardResponse[RoomDetailResponse],
    summary="Get room details",
)
async def get_room(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("rooms.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[RoomDetailResponse]:
    """Retrieve room details including building information."""
    detail = await RoomService.get_room(
        db=db,
        room_id=id,
        university_id=current_user.university_id,
    )
    return StandardResponse(data=detail)


@router.patch(
    "/rooms/{id}",
    response_model=StandardResponse[RoomDetailResponse],
    summary="Update room details",
)
async def update_room(
    id: uuid.UUID,
    payload: RoomUpdateRequest,
    current_user: Annotated[User, Depends(require_permission("rooms.update"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[RoomDetailResponse]:
    """Update room attributes."""
    detail = await RoomService.update_room(
        db=db,
        room_id=id,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=detail,
        meta={"message": "Room updated successfully."},
    )


@router.post(
    "/rooms/{id}/activate",
    response_model=StandardResponse[RoomDetailResponse],
    summary="Activate room",
)
async def activate_room(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("rooms.update"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[RoomDetailResponse]:
    """Activate an inactive room."""
    detail = await RoomService.set_room_status(
        db=db,
        room_id=id,
        university_id=current_user.university_id,
        status=RoomStatus.ACTIVE,
    )
    return StandardResponse(
        data=detail,
        meta={"message": "Room activated successfully."},
    )


@router.post(
    "/rooms/{id}/deactivate",
    response_model=StandardResponse[RoomDetailResponse],
    summary="Deactivate room",
)
async def deactivate_room(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("rooms.deactivate"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[RoomDetailResponse]:
    """Deactivate a room without destroying historical class occurrences."""
    detail = await RoomService.set_room_status(
        db=db,
        room_id=id,
        university_id=current_user.university_id,
        status=RoomStatus.INACTIVE,
    )
    return StandardResponse(
        data=detail,
        meta={"message": "Room deactivated successfully."},
    )
