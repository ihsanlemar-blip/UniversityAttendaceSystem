"""RBAC API router for roles, permissions, and scoped user role assignments."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.schemas import StandardResponse
from backend.app.core.database import get_db_session
from backend.app.core.exceptions import ConflictException, NotFoundException
from backend.app.models.permission import Permission
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.role_permission import RolePermission
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_permission
from backend.app.rbac.schemas import (
    CreateRoleAssignmentRequest,
    CreateRoleRequest,
    PermissionResponse,
    RevokeRoleAssignmentRequest,
    RoleAssignmentResponse,
    RolePermissionUpdateRequest,
    RoleResponse,
)
from backend.app.rbac.service import RbacService

router = APIRouter(prefix="", tags=["RBAC & Authorization"])


@router.get(
    "/roles",
    response_model=StandardResponse[list[RoleResponse]],
    status_code=status.HTTP_200_OK,
    summary="List all available roles",
)
async def list_roles(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_permission("roles.read"))],
) -> StandardResponse[list[RoleResponse]]:
    """Fetch all system and university roles."""
    stmt = select(Role).order_by(Role.code)
    res = await db.execute(stmt)
    roles = res.scalars().all()
    return StandardResponse(
        data=[RoleResponse.model_validate(r, from_attributes=True) for r in roles]
    )


@router.post(
    "/roles",
    response_model=StandardResponse[RoleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create custom role",
)
async def create_role(
    payload: CreateRoleRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_permission("roles.create"))],
) -> StandardResponse[RoleResponse]:
    """Create a new role definition."""
    stmt = select(Role).where(Role.code == payload.code)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise ConflictException(f"Role with code '{payload.code}' already exists.")

    role = Role(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        is_system=False,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return StandardResponse(data=RoleResponse.model_validate(role, from_attributes=True))


@router.get(
    "/roles/{role_id}",
    response_model=StandardResponse[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="Get role details by ID",
)
async def get_role(
    role_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_permission("roles.read"))],
) -> StandardResponse[RoleResponse]:
    """Fetch single role by identifier."""
    role = await db.get(Role, role_id)
    if not role:
        raise NotFoundException("Role", role_id)
    return StandardResponse(data=RoleResponse.model_validate(role, from_attributes=True))


@router.get(
    "/permissions",
    response_model=StandardResponse[list[PermissionResponse]],
    status_code=status.HTTP_200_OK,
    summary="List all permissions",
)
async def list_permissions(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_permission("permissions.read"))],
) -> StandardResponse[list[PermissionResponse]]:
    """Fetch all atomic permission capabilities."""
    stmt = select(Permission).order_by(Permission.code)
    res = await db.execute(stmt)
    perms = res.scalars().all()
    return StandardResponse(
        data=[PermissionResponse.model_validate(p, from_attributes=True) for p in perms]
    )


@router.get(
    "/roles/{role_id}/permissions",
    response_model=StandardResponse[list[PermissionResponse]],
    status_code=status.HTTP_200_OK,
    summary="List permissions assigned to role",
)
async def get_role_permissions(
    role_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_permission("roles.read"))],
) -> StandardResponse[list[PermissionResponse]]:
    """Fetch all permissions associated with a specific role."""
    role = await db.get(Role, role_id)
    if not role:
        raise NotFoundException("Role", role_id)

    stmt = (
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.code)
    )
    res = await db.execute(stmt)
    perms = res.scalars().all()
    return StandardResponse(
        data=[PermissionResponse.model_validate(p, from_attributes=True) for p in perms]
    )


@router.put(
    "/roles/{role_id}/permissions",
    response_model=StandardResponse[list[PermissionResponse]],
    status_code=status.HTTP_200_OK,
    summary="Update permissions assigned to role",
)
async def update_role_permissions(
    role_id: uuid.UUID,
    payload: RolePermissionUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_permission("roles.update"))],
) -> StandardResponse[list[PermissionResponse]]:
    """Replace all permissions assigned to a role."""
    role = await db.get(Role, role_id)
    if not role:
        raise NotFoundException("Role", role_id)

    # Clear current mappings
    stmt_del = delete(RolePermission).where(RolePermission.role_id == role_id)
    await db.execute(stmt_del)

    # Insert new mappings
    for perm_id in payload.permission_ids:
        perm = await db.get(Permission, perm_id)
        if not perm:
            raise NotFoundException("Permission", perm_id)
        db.add(RolePermission(role_id=role_id, permission_id=perm_id))

    await db.commit()

    # Return updated list
    stmt = (
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.code)
    )
    res = await db.execute(stmt)
    perms = res.scalars().all()
    return StandardResponse(
        data=[PermissionResponse.model_validate(p, from_attributes=True) for p in perms]
    )


@router.get(
    "/users/{user_id}/role-assignments",
    response_model=StandardResponse[list[RoleAssignmentResponse]],
    status_code=status.HTTP_200_OK,
    summary="List role assignments for user",
)
async def list_user_role_assignments(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_permission("role_assignments.read"))],
) -> StandardResponse[list[RoleAssignmentResponse]]:
    """Fetch all active and historical role assignments for a user."""
    stmt = (
        select(RoleAssignment)
        .where(RoleAssignment.user_id == user_id)
        .order_by(RoleAssignment.assigned_at.desc())
    )
    res = await db.execute(stmt)
    assignments = res.scalars().all()
    return StandardResponse(
        data=[RoleAssignmentResponse.model_validate(a, from_attributes=True) for a in assignments]
    )


@router.post(
    "/users/{user_id}/role-assignments",
    response_model=StandardResponse[RoleAssignmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Assign role to user",
)
async def assign_role_to_user(
    user_id: uuid.UUID,
    payload: CreateRoleAssignmentRequest,
    current_user: Annotated[User, Depends(require_permission("role_assignments.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[RoleAssignmentResponse]:
    """Assign role to user within current university scope."""
    assignment = await RbacService.assign_role(
        db=db,
        user_id=user_id,
        role_id=payload.role_id,
        university_id=current_user.university_id,
        assigned_by=current_user.id,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
    )
    return StandardResponse(
        data=RoleAssignmentResponse.model_validate(assignment, from_attributes=True)
    )


@router.delete(
    "/role-assignments/{assignment_id}",
    response_model=StandardResponse[RoleAssignmentResponse],
    status_code=status.HTTP_200_OK,
    summary="Revoke role assignment",
)
async def revoke_role_assignment(
    assignment_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("role_assignments.manage"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    payload: RevokeRoleAssignmentRequest | None = None,
) -> StandardResponse[RoleAssignmentResponse]:
    """Revoke an active role assignment while preserving historical audit records."""
    reason = payload.reason if payload else "ADMIN_REVOKED"
    assignment = await RbacService.revoke_role_assignment(
        db=db,
        assignment_id=assignment_id,
        revoked_by=current_user.id,
        reason=reason,
    )
    return StandardResponse(
        data=RoleAssignmentResponse.model_validate(assignment, from_attributes=True)
    )
