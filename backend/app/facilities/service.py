"""Facilities service managing campus buildings and room spaces."""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.core.constants import BuildingStatus, RoomStatus
from backend.app.core.exceptions import ConflictException, NotFoundException
from backend.app.core.logging import get_logger
from backend.app.facilities.schemas import (
    BuildingCreateRequest,
    BuildingResponse,
    BuildingUpdateRequest,
    RoomCreateRequest,
    RoomDetailResponse,
    RoomUpdateRequest,
)
from backend.app.models.building import Building
from backend.app.models.room import Room

logger = get_logger(__name__)


class BuildingService:
    """Service handling campus building master data business logic."""

    @staticmethod
    async def create_building(
        db: AsyncSession,
        university_id: uuid.UUID,
        payload: BuildingCreateRequest,
    ) -> Building:
        """Create a new campus building with normalized code uniqueness check."""
        normalized_code = payload.code.strip().upper()
        stmt = select(Building).where(
            Building.university_id == university_id,
            func.upper(Building.code) == normalized_code,
        )
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise ConflictException(
                "Building with this code already exists in the university.",
                details={"code": normalized_code},
            )

        building = Building(
            university_id=university_id,
            code=normalized_code,
            name=payload.name.strip(),
            status=BuildingStatus.ACTIVE.value,
        )
        db.add(building)
        await db.commit()
        await db.refresh(building)
        logger.info(f"BUILDING_CREATED id={building.id} code={building.code}")
        return building

    @staticmethod
    async def get_building(
        db: AsyncSession,
        building_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> Building:
        """Retrieve a specific building by ID within university boundary."""
        stmt = select(Building).where(
            Building.id == building_id,
            Building.university_id == university_id,
        )
        res = await db.execute(stmt)
        building = res.scalar_one_or_none()
        if not building:
            raise NotFoundException("Building", building_id)
        return building

    @staticmethod
    async def list_buildings(
        db: AsyncSession,
        university_id: uuid.UUID,
        pagination: PaginationParams,
        status: BuildingStatus | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[BuildingResponse]:
        """List paginated buildings for a university with optional filters."""
        query = select(Building).where(Building.university_id == university_id)

        if status:
            query = query.where(Building.status == status.value)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Building.name.ilike(term),
                    Building.code.ilike(term),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        # Query page items
        query = query.order_by(Building.code.asc())
        query = query.offset(pagination.offset).limit(pagination.page_size)
        items_res = await db.execute(query)
        buildings = items_res.scalars().all()

        item_responses = [BuildingResponse.model_validate(b) for b in buildings]
        return PaginatedResponse.create(
            items=item_responses,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    @staticmethod
    async def update_building(
        db: AsyncSession,
        building_id: uuid.UUID,
        university_id: uuid.UUID,
        payload: BuildingUpdateRequest,
    ) -> Building:
        """Update building attributes."""
        building = await BuildingService.get_building(db, building_id, university_id)

        if payload.name is not None:
            building.name = payload.name.strip()
        if payload.status is not None:
            building.status = payload.status.value

        await db.commit()
        await db.refresh(building)
        logger.info(f"BUILDING_UPDATED id={building.id} code={building.code}")
        return building

    @staticmethod
    async def set_building_status(
        db: AsyncSession,
        building_id: uuid.UUID,
        university_id: uuid.UUID,
        status: BuildingStatus,
    ) -> Building:
        """Update building operational status."""
        building = await BuildingService.get_building(db, building_id, university_id)
        building.status = status.value
        await db.commit()
        await db.refresh(building)
        logger.info(f"BUILDING_STATUS_CHANGED id={building.id} status={building.status}")
        return building


class RoomService:
    """Service handling campus room and classroom facility business logic."""

    @staticmethod
    async def create_room(
        db: AsyncSession,
        university_id: uuid.UUID,
        payload: RoomCreateRequest,
    ) -> Room:
        """Create a new room with building validation and room_number uniqueness."""
        # 1. Validate building belongs to the same university
        building_stmt = select(Building).where(
            Building.id == payload.building_id,
            Building.university_id == university_id,
        )
        b_res = await db.execute(building_stmt)
        building = b_res.scalar_one_or_none()
        if not building:
            raise NotFoundException("Building", payload.building_id)

        # 2. Check room_number uniqueness within building
        normalized_num = payload.room_number.strip()
        stmt = select(Room).where(
            Room.building_id == payload.building_id,
            func.lower(Room.room_number) == normalized_num.lower(),
        )
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise ConflictException(
                "Room with this number already exists in this building.",
                details={"room_number": normalized_num},
            )

        room = Room(
            university_id=university_id,
            building_id=payload.building_id,
            room_number=normalized_num,
            name=payload.name.strip() if payload.name else None,
            capacity=payload.capacity,
            room_type=payload.room_type,
            floor=payload.floor.strip() if payload.floor else None,
            status=RoomStatus.ACTIVE.value,
        )
        db.add(room)
        await db.commit()
        await db.refresh(room)
        logger.info(
            f"ROOM_CREATED id={room.id} number={room.room_number} building_id={building.id}"
        )
        return room

    @staticmethod
    async def get_room(
        db: AsyncSession,
        room_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> RoomDetailResponse:
        """Retrieve a specific room with building details by ID."""
        stmt = (
            select(Room)
            .options(selectinload(Room.building))
            .where(
                Room.id == room_id,
                Room.university_id == university_id,
            )
        )
        res = await db.execute(stmt)
        room = res.scalar_one_or_none()
        if not room:
            raise NotFoundException("Room", room_id)

        detail = RoomDetailResponse.model_validate(room)
        if room.building:
            detail.building_name = room.building.name
            detail.building_code = room.building.code
        return detail

    @staticmethod
    async def list_rooms(
        db: AsyncSession,
        university_id: uuid.UUID,
        pagination: PaginationParams,
        building_id: uuid.UUID | None = None,
        status: RoomStatus | None = None,
        capacity_min: int | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[RoomDetailResponse]:
        """List paginated rooms for a university with optional filters."""
        query = (
            select(Room)
            .options(selectinload(Room.building))
            .where(Room.university_id == university_id)
        )

        if building_id:
            query = query.where(Room.building_id == building_id)

        if status:
            query = query.where(Room.status == status.value)

        if capacity_min is not None:
            query = query.where(Room.capacity >= capacity_min)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Room.room_number.ilike(term),
                    Room.name.ilike(term),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        # Query page items
        query = query.order_by(Room.room_number.asc())
        query = query.offset(pagination.offset).limit(pagination.page_size)
        items_res = await db.execute(query)
        rooms = items_res.scalars().all()

        details: list[RoomDetailResponse] = []
        for r in rooms:
            d = RoomDetailResponse.model_validate(r)
            if r.building:
                d.building_name = r.building.name
                d.building_code = r.building.code
            details.append(d)

        return PaginatedResponse.create(
            items=details,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    @staticmethod
    async def update_room(
        db: AsyncSession,
        room_id: uuid.UUID,
        university_id: uuid.UUID,
        payload: RoomUpdateRequest,
    ) -> RoomDetailResponse:
        """Update room details and validate room number uniqueness if changed."""
        stmt = (
            select(Room)
            .options(selectinload(Room.building))
            .where(
                Room.id == room_id,
                Room.university_id == university_id,
            )
        )
        res = await db.execute(stmt)
        room = res.scalar_one_or_none()
        if not room:
            raise NotFoundException("Room", room_id)

        if payload.room_number is not None:
            normalized_num = payload.room_number.strip()
            if normalized_num.lower() != room.room_number.lower():
                dup_stmt = select(Room).where(
                    Room.building_id == room.building_id,
                    Room.id != room.id,
                    func.lower(Room.room_number) == normalized_num.lower(),
                )
                dup_res = await db.execute(dup_stmt)
                if dup_res.scalar_one_or_none():
                    raise ConflictException(
                        "Room with this number already exists in this building.",
                        details={"room_number": normalized_num},
                    )
                room.room_number = normalized_num

        if payload.name is not None:
            room.name = payload.name.strip() if payload.name else None
        if payload.capacity is not None:
            room.capacity = payload.capacity
        if payload.room_type is not None:
            room.room_type = payload.room_type
        if payload.floor is not None:
            room.floor = payload.floor.strip() if payload.floor else None
        if payload.status is not None:
            room.status = payload.status.value

        await db.commit()
        await db.refresh(room)
        logger.info(f"ROOM_UPDATED id={room.id} number={room.room_number}")

        detail = RoomDetailResponse.model_validate(room)
        if room.building:
            detail.building_name = room.building.name
            detail.building_code = room.building.code
        return detail

    @staticmethod
    async def set_room_status(
        db: AsyncSession,
        room_id: uuid.UUID,
        university_id: uuid.UUID,
        status: RoomStatus,
    ) -> RoomDetailResponse:
        """Update room operational status (safe deactivation preserving historical references)."""
        stmt = (
            select(Room)
            .options(selectinload(Room.building))
            .where(
                Room.id == room_id,
                Room.university_id == university_id,
            )
        )
        res = await db.execute(stmt)
        room = res.scalar_one_or_none()
        if not room:
            raise NotFoundException("Room", room_id)

        room.status = status.value
        await db.commit()
        await db.refresh(room)
        logger.info(f"ROOM_STATUS_CHANGED id={room.id} status={room.status}")

        detail = RoomDetailResponse.model_validate(room)
        if room.building:
            detail.building_name = room.building.name
            detail.building_code = room.building.code
        return detail
