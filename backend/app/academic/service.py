"""Academic unit domain service managing hierarchy, cycle prevention, and lifecycle."""

import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.academic.schemas import (
    AcademicUnitCreateRequest,
    AcademicUnitDetailResponse,
    AcademicUnitMoveRequest,
    AcademicUnitResponse,
    AcademicUnitTreeNodeResponse,
    AcademicUnitUpdateRequest,
)
from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.core.constants import RecordStatus
from backend.app.core.exceptions import ConflictException, DomainException, NotFoundException
from backend.app.models.academic_unit import AcademicUnit


class AcademicUnitService:
    """Service handling academic unit hierarchy operations and business logic."""

    @staticmethod
    async def validate_no_cycle(
        db: AsyncSession,
        university_id: uuid.UUID,
        unit_id: uuid.UUID,
        target_parent_id: uuid.UUID | None,
    ) -> None:
        """Ensure reparenting does not introduce circular references.

        Validates:
        1. target_parent_id != unit_id (self-parenting).
        2. target_parent_id exists and belongs to same university.
        3. unit_id does not appear anywhere in target_parent_id's ancestor chain.
        """
        if target_parent_id is None:
            return

        if target_parent_id == unit_id:
            raise DomainException(
                code="ACADEMIC_UNIT_CYCLE",
                message="An academic unit cannot be its own parent.",
                status_code=400,
                details={"unit_id": str(unit_id), "target_parent_id": str(target_parent_id)},
            )

        parent = await db.get(AcademicUnit, target_parent_id)
        if not parent or parent.university_id != university_id:
            raise DomainException(
                code="INVALID_PARENT_UNIT",
                message="Parent unit not found within current university.",
                status_code=400,
                details={"target_parent_id": str(target_parent_id)},
            )

        # Traverse upwards from parent to detect cycle
        visited: set[uuid.UUID] = {target_parent_id}
        curr_id: uuid.UUID | None = parent.parent_id

        while curr_id is not None:
            if curr_id == unit_id:
                raise DomainException(
                    code="ACADEMIC_UNIT_CYCLE",
                    message="Cycle detected: cannot assign a descendant unit as parent.",
                    status_code=400,
                    details={"unit_id": str(unit_id), "cycle_at": str(curr_id)},
                )
            if curr_id in visited:
                raise DomainException(
                    code="ACADEMIC_UNIT_CYCLE",
                    message="Circular reference detected in existing hierarchy.",
                    status_code=400,
                    details={"cycle_at": str(curr_id)},
                )
            visited.add(curr_id)
            ancestor = await db.get(AcademicUnit, curr_id)
            if not ancestor or ancestor.university_id != university_id:
                break
            curr_id = ancestor.parent_id

    @staticmethod
    async def create_unit(
        db: AsyncSession,
        university_id: uuid.UUID,
        payload: AcademicUnitCreateRequest,
    ) -> AcademicUnit:
        """Create a new academic unit with code uniqueness and cycle check."""
        # 1. Uniqueness check
        stmt = select(AcademicUnit).where(
            AcademicUnit.university_id == university_id,
            AcademicUnit.code == payload.code,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ConflictException(
                f"Academic unit with code '{payload.code}' already exists in this university.",
                details={"code": payload.code},
            )

        # 2. Parent validation if specified
        if payload.parent_id:
            parent = await db.get(AcademicUnit, payload.parent_id)
            if not parent or parent.university_id != university_id:
                raise DomainException(
                    code="INVALID_PARENT_UNIT",
                    message="Parent unit not found within current university.",
                    status_code=400,
                    details={"parent_id": str(payload.parent_id)},
                )
            if parent.status != RecordStatus.ACTIVE.value:
                raise DomainException(
                    code="PARENT_UNIT_INACTIVE",
                    message="Cannot create child unit under an inactive or archived parent.",
                    status_code=400,
                    details={"parent_id": str(payload.parent_id)},
                )

        unit = AcademicUnit(
            university_id=university_id,
            parent_id=payload.parent_id,
            unit_type=payload.unit_type.value,
            code=payload.code,
            name=payload.name,
            short_name=payload.short_name,
            sort_order=payload.sort_order,
            status=RecordStatus.ACTIVE.value,
        )
        db.add(unit)
        await db.commit()
        await db.refresh(unit)
        return unit

    @staticmethod
    async def get_unit_by_id(
        db: AsyncSession,
        university_id: uuid.UUID,
        unit_id: uuid.UUID,
    ) -> AcademicUnitDetailResponse:
        """Fetch academic unit details including parent, child count, and ancestor path."""
        unit = await db.get(AcademicUnit, unit_id)
        if not unit or unit.university_id != university_id:
            raise NotFoundException("AcademicUnit", unit_id)

        # Child count
        child_count_stmt = select(func.count(AcademicUnit.id)).where(
            AcademicUnit.parent_id == unit_id,
            AcademicUnit.status == RecordStatus.ACTIVE.value,
        )
        child_count = (await db.execute(child_count_stmt)).scalar_one() or 0

        # Parent info
        parent_resp: AcademicUnitResponse | None = None
        if unit.parent_id:
            parent = await db.get(AcademicUnit, unit.parent_id)
            if parent and parent.university_id == university_id:
                parent_resp = AcademicUnitResponse.model_validate(parent)

        # Ancestor breadcrumb path (from immediate parent up to root)
        ancestor_path: list[AcademicUnitResponse] = []
        curr_id: uuid.UUID | None = unit.parent_id
        while curr_id is not None:
            anc = await db.get(AcademicUnit, curr_id)
            if not anc or anc.university_id != university_id:
                break
            ancestor_path.append(AcademicUnitResponse.model_validate(anc))
            curr_id = anc.parent_id

        # Reverse so path is root -> ... -> immediate parent
        ancestor_path.reverse()

        return AcademicUnitDetailResponse(
            id=unit.id,
            university_id=unit.university_id,
            parent_id=unit.parent_id,
            unit_type=unit.unit_type,
            code=unit.code,
            name=unit.name,
            short_name=unit.short_name,
            status=unit.status,
            sort_order=unit.sort_order,
            created_at=unit.created_at,
            updated_at=unit.updated_at,
            parent=parent_resp,
            children_count=child_count,
            ancestor_path=ancestor_path,
        )

    @staticmethod
    async def list_units(
        db: AsyncSession,
        university_id: uuid.UUID,
        page_params: PaginationParams,
        parent_id: uuid.UUID | None = None,
        is_root_only: bool = False,
        unit_type: str | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[AcademicUnitResponse]:
        """List academic units matching query filters with pagination."""
        query = select(AcademicUnit).where(AcademicUnit.university_id == university_id)

        if is_root_only:
            query = query.where(AcademicUnit.parent_id.is_(None))
        elif parent_id is not None:
            query = query.where(AcademicUnit.parent_id == parent_id)

        if unit_type:
            query = query.where(AcademicUnit.unit_type == unit_type)

        if status:
            query = query.where(AcademicUnit.status == status)

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar_one() or 0

        # Paginated fetch
        query = (
            query.order_by(AcademicUnit.sort_order.asc(), AcademicUnit.name.asc())
            .offset(page_params.offset)
            .limit(page_params.page_size)
        )
        res = await db.execute(query)
        units = res.scalars().all()

        items = [AcademicUnitResponse.model_validate(u) for u in units]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    @staticmethod
    async def get_unit_tree(
        db: AsyncSession,
        university_id: uuid.UUID,
        root_id: uuid.UUID | None = None,
    ) -> list[AcademicUnitTreeNodeResponse]:
        """Construct hierarchical organizational tree in a single query without N+1 explosion."""
        stmt = (
            select(AcademicUnit)
            .where(
                AcademicUnit.university_id == university_id,
                AcademicUnit.status == RecordStatus.ACTIVE.value,
            )
            .order_by(AcademicUnit.sort_order.asc(), AcademicUnit.name.asc())
        )
        res = await db.execute(stmt)
        all_units = res.scalars().all()

        # Group children by parent_id
        children_map: dict[uuid.UUID | None, list[AcademicUnit]] = defaultdict(list)
        unit_map: dict[uuid.UUID, AcademicUnit] = {}

        for u in all_units:
            unit_map[u.id] = u
            children_map[u.parent_id].append(u)

        def build_node(unit: AcademicUnit) -> AcademicUnitTreeNodeResponse:
            child_units = children_map.get(unit.id, [])
            return AcademicUnitTreeNodeResponse(
                id=unit.id,
                code=unit.code,
                name=unit.name,
                short_name=unit.short_name,
                unit_type=unit.unit_type,
                status=unit.status,
                sort_order=unit.sort_order,
                children=[build_node(child) for child in child_units],
            )

        if root_id is not None:
            root_unit = unit_map.get(root_id)
            if not root_unit:
                raise NotFoundException("AcademicUnit", root_id)
            return [build_node(root_unit)]

        # Return all top-level root units
        root_units = children_map.get(None, [])
        return [build_node(r) for r in root_units]

    @staticmethod
    async def update_unit(
        db: AsyncSession,
        university_id: uuid.UUID,
        unit_id: uuid.UUID,
        payload: AcademicUnitUpdateRequest,
    ) -> AcademicUnit:
        """Update academic unit attributes."""
        unit = await db.get(AcademicUnit, unit_id)
        if not unit or unit.university_id != university_id:
            raise NotFoundException("AcademicUnit", unit_id)

        if payload.code is not None and payload.code != unit.code:
            stmt = select(AcademicUnit).where(
                AcademicUnit.university_id == university_id,
                AcademicUnit.code == payload.code,
                AcademicUnit.id != unit_id,
            )
            if (await db.execute(stmt)).scalar_one_or_none():
                raise ConflictException(
                    f"Academic unit with code '{payload.code}' already exists in this university.",
                    details={"code": payload.code},
                )
            unit.code = payload.code

        if payload.name is not None:
            unit.name = payload.name
        if payload.unit_type is not None:
            unit.unit_type = payload.unit_type.value
        if payload.short_name is not None:
            unit.short_name = payload.short_name
        if payload.sort_order is not None:
            unit.sort_order = payload.sort_order

        await db.commit()
        await db.refresh(unit)
        return unit

    @staticmethod
    async def move_unit(
        db: AsyncSession,
        university_id: uuid.UUID,
        unit_id: uuid.UUID,
        payload: AcademicUnitMoveRequest,
    ) -> AcademicUnit:
        """Reparent academic unit with cycle prevention."""
        unit = await db.get(AcademicUnit, unit_id)
        if not unit or unit.university_id != university_id:
            raise NotFoundException("AcademicUnit", unit_id)

        if payload.parent_id == unit.parent_id:
            return unit

        # Perform cycle and validity checks
        await AcademicUnitService.validate_no_cycle(
            db=db,
            university_id=university_id,
            unit_id=unit_id,
            target_parent_id=payload.parent_id,
        )

        unit.parent_id = payload.parent_id
        await db.commit()
        await db.refresh(unit)
        return unit

    @staticmethod
    async def deactivate_unit(
        db: AsyncSession,
        university_id: uuid.UUID,
        unit_id: uuid.UUID,
    ) -> AcademicUnit:
        """Soft-deactivate an academic unit if no active children exist."""
        unit = await db.get(AcademicUnit, unit_id)
        if not unit or unit.university_id != university_id:
            raise NotFoundException("AcademicUnit", unit_id)

        # Check for active children
        stmt = select(AcademicUnit).where(
            AcademicUnit.parent_id == unit_id,
            AcademicUnit.status == RecordStatus.ACTIVE.value,
        )
        active_children = (await db.execute(stmt)).scalars().all()
        if active_children:
            raise DomainException(
                code="ACADEMIC_UNIT_HAS_ACTIVE_CHILDREN",
                message="Cannot deactivate academic unit while it has active child units.",
                status_code=400,
                details={"active_children_count": len(active_children)},
            )

        unit.status = RecordStatus.ARCHIVED.value
        await db.commit()
        await db.refresh(unit)
        return unit

    @staticmethod
    async def activate_unit(
        db: AsyncSession,
        university_id: uuid.UUID,
        unit_id: uuid.UUID,
    ) -> AcademicUnit:
        """Reactivate an academic unit ensuring its parent is active."""
        unit = await db.get(AcademicUnit, unit_id)
        if not unit or unit.university_id != university_id:
            raise NotFoundException("AcademicUnit", unit_id)

        if unit.parent_id:
            parent = await db.get(AcademicUnit, unit.parent_id)
            if not parent or parent.status != RecordStatus.ACTIVE.value:
                raise DomainException(
                    code="PARENT_UNIT_INACTIVE",
                    message="Cannot activate academic unit whose parent is inactive.",
                    status_code=400,
                    details={"parent_id": str(unit.parent_id)},
                )

        unit.status = RecordStatus.ACTIVE.value
        await db.commit()
        await db.refresh(unit)
        return unit
