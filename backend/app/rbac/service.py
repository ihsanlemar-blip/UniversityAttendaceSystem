"""RBAC service for managing roles, permissions, and evaluating user authorization."""

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.types import utc_now
from backend.app.core.constants import RecordStatus, ScopeType
from backend.app.core.exceptions import ConflictException, NotFoundException, ValidationException
from backend.app.models.academic_unit import AcademicUnit
from backend.app.models.permission import Permission
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.role_permission import RolePermission
from backend.app.models.user import User


class RbacService:
    """Service evaluating role-based permissions and scoped assignments."""

    @staticmethod
    async def get_user_roles(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
        """Fetch list of active, non-revoked role codes assigned to user."""
        stmt = (
            select(Role.code)
            .join(RoleAssignment, RoleAssignment.role_id == Role.id)
            .where(
                RoleAssignment.user_id == user_id,
                RoleAssignment.revoked_at.is_(None),
            )
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_user_permissions(db: AsyncSession, user_id: uuid.UUID) -> set[str]:
        """Fetch set of active, non-revoked permission codes granted to user."""
        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(RoleAssignment, RoleAssignment.role_id == Role.id)
            .where(
                RoleAssignment.user_id == user_id,
                RoleAssignment.revoked_at.is_(None),
            )
        )
        res = await db.execute(stmt)
        return set(res.scalars().all())

    @staticmethod
    async def has_permission(
        db: AsyncSession,
        user_id: uuid.UUID,
        permission_code: str,
        university_id: uuid.UUID,
        allow_scoped: bool = False,
    ) -> bool:
        """Evaluate if user possesses effective permission in university scope.

        Enforces default-deny: returns True only if an active role assignment
        in the target university grants the requested permission.
        If allow_scoped is True, role assignments at ACADEMIC_UNIT scope also qualify.
        """
        stmt = (
            select(Permission.id)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(RoleAssignment, RoleAssignment.role_id == Role.id)
            .where(
                RoleAssignment.user_id == user_id,
                RoleAssignment.university_id == university_id,
                RoleAssignment.revoked_at.is_(None),
                Permission.code == permission_code,
            )
        )
        if not allow_scoped:
            stmt = stmt.where(RoleAssignment.scope_type == ScopeType.UNIVERSITY.value)

        stmt = stmt.limit(1)
        res = await db.execute(stmt)
        return res.scalar_one_or_none() is not None

    @staticmethod
    async def has_academic_unit_permission(
        db: AsyncSession,
        user_id: uuid.UUID,
        permission_code: str,
        university_id: uuid.UUID,
        target_unit_id: uuid.UUID,
    ) -> bool:
        """Evaluate if user has permission on target academic unit or any of its ancestors.

        1. University-scoped assignment grants authority over all units in the university.
        2. Academic-unit-scoped assignment grants authority over the unit and its subtree.
        3. Access to sibling, ancestor, or unrelated units is denied.
        """
        # 1. University-wide permission grants access to all units
        if await RbacService.has_permission(
            db=db,
            user_id=user_id,
            permission_code=permission_code,
            university_id=university_id,
        ):
            return True

        # 2. Check academic-unit-scoped assignments
        stmt = (
            select(RoleAssignment.scope_id)
            .join(Role, Role.id == RoleAssignment.role_id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(
                RoleAssignment.user_id == user_id,
                RoleAssignment.university_id == university_id,
                RoleAssignment.scope_type == ScopeType.ACADEMIC_UNIT.value,
                RoleAssignment.revoked_at.is_(None),
                Permission.code == permission_code,
            )
        )
        res = await db.execute(stmt)
        allowed_unit_ids = set(res.scalars().all())

        if not allowed_unit_ids:
            return False

        if target_unit_id in allowed_unit_ids:
            return True

        # 3. Traverse ancestor chain of target_unit_id
        curr_id: uuid.UUID | None = target_unit_id
        while curr_id is not None:
            unit = await db.get(AcademicUnit, curr_id)
            if not unit or unit.university_id != university_id:
                break
            if unit.id in allowed_unit_ids:
                return True
            curr_id = unit.parent_id

        return False

    @staticmethod
    async def get_accessible_academic_unit_ids(
        db: AsyncSession,
        user_id: uuid.UUID,
        permission_code: str,
        university_id: uuid.UUID,
    ) -> set[uuid.UUID] | None:
        """Return set of academic unit IDs accessible to user for given permission.

        Returns:
            None: If user has university-wide permission (unbounded access).
            set[uuid.UUID]: Set of allowed unit IDs including subtree descendants.
            Empty set: If user has no permission.
        """
        if await RbacService.has_permission(
            db=db,
            user_id=user_id,
            permission_code=permission_code,
            university_id=university_id,
        ):
            return None

        stmt = (
            select(RoleAssignment.scope_id)
            .join(Role, Role.id == RoleAssignment.role_id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(
                RoleAssignment.user_id == user_id,
                RoleAssignment.university_id == university_id,
                RoleAssignment.scope_type == ScopeType.ACADEMIC_UNIT.value,
                RoleAssignment.revoked_at.is_(None),
                Permission.code == permission_code,
            )
        )
        res = await db.execute(stmt)
        base_unit_ids = set(res.scalars().all())
        if not base_unit_ids:
            return set()

        # Fetch all units in the university to expand descendants
        units_stmt = select(AcademicUnit.id, AcademicUnit.parent_id).where(
            AcademicUnit.university_id == university_id
        )
        all_units = (await db.execute(units_stmt)).all()

        # Build adjacency list: parent_id -> list of child_ids
        children_map: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
        for u_id, p_id in all_units:
            if p_id is not None:
                children_map[p_id].append(u_id)

        # BFS/DFS expand all descendants
        expanded: set[uuid.UUID] = set(base_unit_ids)
        queue = list(base_unit_ids)
        while queue:
            parent = queue.pop(0)
            for child in children_map.get(parent, []):
                if child not in expanded:
                    expanded.add(child)
                    queue.append(child)

        return expanded

    @staticmethod
    async def assign_role(
        db: AsyncSession,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        university_id: uuid.UUID,
        assigned_by: uuid.UUID | None,
        scope_type: str = ScopeType.UNIVERSITY.value,
        scope_id: uuid.UUID | None = None,
    ) -> RoleAssignment:
        """Assign role to user with institutional or academic unit scope."""
        if scope_type == ScopeType.UNIVERSITY.value:
            resolved_scope_id = scope_id or university_id
            if resolved_scope_id != university_id:
                raise ValidationException(
                    "Scope ID must match target university_id for UNIVERSITY scope.",
                    details={
                        "scope_id": str(resolved_scope_id),
                        "university_id": str(university_id),
                    },
                )
        elif scope_type == ScopeType.ACADEMIC_UNIT.value:
            if not scope_id:
                raise ValidationException(
                    "scope_id is required for ACADEMIC_UNIT scope.",
                    details={"scope_type": scope_type},
                )
            unit = await db.get(AcademicUnit, scope_id)
            if not unit or unit.university_id != university_id:
                raise ValidationException(
                    "Specified academic unit does not exist in the target university.",
                    details={"scope_id": str(scope_id), "university_id": str(university_id)},
                )
            if unit.status != RecordStatus.ACTIVE.value:
                raise ValidationException(
                    "Cannot assign roles to an inactive or archived academic unit.",
                    details={"scope_id": str(scope_id), "status": unit.status},
                )
            resolved_scope_id = scope_id
        else:
            raise ValidationException(
                f"Scope type '{scope_type}' is not supported. "
                "Allowed scopes are 'UNIVERSITY' and 'ACADEMIC_UNIT'.",
                details={"scope_type": scope_type},
            )

        # Verify user and role exist
        user = await db.get(User, user_id)
        if not user:
            raise NotFoundException("User", user_id)

        role = await db.get(Role, role_id)
        if not role:
            raise NotFoundException("Role", role_id)

        # Check for active duplicate assignment
        stmt = select(RoleAssignment).where(
            RoleAssignment.user_id == user_id,
            RoleAssignment.role_id == role_id,
            RoleAssignment.university_id == university_id,
            RoleAssignment.scope_type == scope_type,
            RoleAssignment.scope_id == resolved_scope_id,
            RoleAssignment.revoked_at.is_(None),
        )
        res = await db.execute(stmt)
        if res.scalar_one_or_none() is not None:
            raise ConflictException(
                "User already has an active assignment for this role in this scope.",
                details={"user_id": str(user_id), "role_id": str(role_id)},
            )

        assignment = RoleAssignment(
            user_id=user_id,
            role_id=role_id,
            university_id=university_id,
            scope_type=scope_type,
            scope_id=resolved_scope_id,
            assigned_at=utc_now(),
            assigned_by=assigned_by,
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)
        return assignment

    @staticmethod
    async def revoke_role_assignment(
        db: AsyncSession,
        assignment_id: uuid.UUID,
        revoked_by: uuid.UUID | None,
        reason: str | None = None,
    ) -> RoleAssignment:
        """Revoke role assignment while preserving audit history."""
        assignment = await db.get(RoleAssignment, assignment_id)
        if not assignment:
            raise NotFoundException("RoleAssignment", assignment_id)

        if assignment.revoked_at is not None:
            raise ConflictException(
                "Role assignment has already been revoked.",
                details={"assignment_id": str(assignment_id)},
            )

        assignment.revoked_at = utc_now()
        assignment.revoked_by = revoked_by
        assignment.revocation_reason = reason or "ADMIN_REVOKED"
        await db.commit()
        await db.refresh(assignment)
        return assignment
