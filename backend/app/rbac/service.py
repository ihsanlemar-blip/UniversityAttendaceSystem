"""RBAC service for managing roles, permissions, and evaluating user authorization."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.types import utc_now
from backend.app.core.constants import ScopeType
from backend.app.core.exceptions import ConflictException, NotFoundException, ValidationException
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
    ) -> bool:
        """Evaluate if user possesses effective permission in university scope.

        Enforces default-deny: returns True only if an active role assignment
        in the target university grants the requested permission.
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
            .limit(1)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none() is not None

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
        """Assign role to user with institutional scope.

        Milestone 5 strictly enforces UNIVERSITY scope.
        """
        if scope_type != ScopeType.UNIVERSITY.value:
            raise ValidationException(
                f"Scope type '{scope_type}' is not supported in Milestone 5. "
                "Only 'UNIVERSITY' is allowed.",
                details={"scope_type": scope_type},
            )

        resolved_scope_id = scope_id or university_id
        if resolved_scope_id != university_id:
            raise ValidationException(
                "Scope ID must match target university_id for UNIVERSITY scope.",
                details={"scope_id": str(resolved_scope_id), "university_id": str(university_id)},
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
