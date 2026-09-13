"""Test suite for RBAC seeding, role assignments, permissions, and access checks."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.passwords import hash_password
from backend.app.core.constants import PermissionCode, ScopeType, SystemRole, UserStatus
from backend.app.models.permission import Permission
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.university import University
from backend.app.models.user import User
from backend.app.rbac.seeding import SYSTEM_PERMISSIONS, SYSTEM_ROLES, seed_system_rbac
from backend.app.rbac.service import RbacService


@pytest.mark.asyncio
async def test_seed_system_rbac_idempotent(db_session: AsyncSession) -> None:
    """Verify system permissions and roles are seeded correctly and idempotently."""
    await seed_system_rbac(db_session)
    await db_session.commit()

    # Verify all permissions exist
    perm_res = await db_session.execute(select(Permission))
    perms = {p.code: p for p in perm_res.scalars().all()}
    for expected_code, expected_desc in SYSTEM_PERMISSIONS:
        assert expected_code in perms
        assert perms[expected_code].description == expected_desc

    # Verify all roles exist
    role_res = await db_session.execute(select(Role))
    roles = {r.code: r for r in role_res.scalars().all()}
    for expected_code, _, _, is_sys in SYSTEM_ROLES:
        assert expected_code in roles
        assert roles[expected_code].is_system is is_sys

    # Verify 8 approved system roles and 21 core platform/academic permissions
    assert len(SYSTEM_ROLES) == 8
    assert len(SYSTEM_PERMISSIONS) == 21
    assert not any("attendance" in p[0] for p in SYSTEM_PERMISSIONS)

    # Re-running seed should not error or duplicate
    await seed_system_rbac(db_session)
    await db_session.commit()


@pytest.mark.asyncio
async def test_super_admin_has_all_permissions(
    db_session: AsyncSession, test_admin_user: User, test_university: University
) -> None:
    """Verify that Super Admin user resolves all system permissions via mapped role."""
    roles = await RbacService.get_user_roles(db_session, test_admin_user.id)
    assert SystemRole.SUPER_ADMIN.value in roles

    perms = await RbacService.get_user_permissions(db_session, test_admin_user.id)
    all_perm_codes = {code for code, _ in SYSTEM_PERMISSIONS}
    assert all_perm_codes.issubset(perms)

    # Individual check
    has_users_read = await RbacService.has_permission(
        db_session,
        test_admin_user.id,
        PermissionCode.USERS_READ.value,
        test_university.id,
    )
    assert has_users_read is True


@pytest.mark.asyncio
async def test_regular_user_deny_by_default(
    db_session: AsyncSession, test_university: University
) -> None:
    """Verify that a newly created user with no role assignments has zero permissions."""
    user = User(
        university_id=test_university.id,
        username=f"unassigned_{uuid.uuid4().hex[:6]}",
        email=f"user_{uuid.uuid4().hex[:6]}@test.edu",
        password_hash=hash_password("RegularPass123!"),
        status=UserStatus.ACTIVE.value,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    roles = await RbacService.get_user_roles(db_session, user.id)
    assert len(roles) == 0

    perms = await RbacService.get_user_permissions(db_session, user.id)
    assert len(perms) == 0

    has_perm = await RbacService.has_permission(
        db_session,
        user.id,
        PermissionCode.USERS_READ.value,
        test_university.id,
    )
    assert has_perm is False


@pytest.mark.asyncio
async def test_assign_and_revoke_role(
    db_session: AsyncSession,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify role assignment, permission expansion, and soft revocation."""
    user = User(
        university_id=test_university.id,
        username=f"auditor_{uuid.uuid4().hex[:6]}",
        email=f"auditor_{uuid.uuid4().hex[:6]}@test.edu",
        password_hash=hash_password("AuditorPass123!"),
        status=UserStatus.ACTIVE.value,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Find AUDITOR role
    role_res = await db_session.execute(select(Role).where(Role.code == SystemRole.AUDITOR.value))
    auditor_role = role_res.scalar_one()

    # Assign AUDITOR role
    assignment = await RbacService.assign_role(
        db_session,
        user_id=user.id,
        role_id=auditor_role.id,
        university_id=test_university.id,
        assigned_by=test_admin_user.id,
        scope_type=ScopeType.UNIVERSITY.value,
        scope_id=test_university.id,
    )
    await db_session.commit()

    assert assignment.user_id == user.id
    assert assignment.role_id == auditor_role.id
    assert assignment.revoked_at is None

    # Check permissions now contain audit:read
    perms = await RbacService.get_user_permissions(db_session, user.id)
    assert PermissionCode.AUDIT_READ.value in perms
    assert PermissionCode.USERS_CREATE.value not in perms

    # Revoke role assignment
    revoked = await RbacService.revoke_role_assignment(
        db_session,
        assignment_id=assignment.id,
        revoked_by=test_admin_user.id,
    )
    await db_session.commit()

    assert revoked.revoked_at is not None
    assert revoked.revoked_by == test_admin_user.id

    # Historical record is preserved in DB
    check_assignment = await db_session.get(RoleAssignment, assignment.id)
    assert check_assignment is not None
    assert check_assignment.revoked_at is not None

    # Effective permissions are now empty
    perms_after = await RbacService.get_user_permissions(db_session, user.id)
    assert len(perms_after) == 0


@pytest.mark.asyncio
async def test_cross_tenant_rbac_isolation(
    db_session: AsyncSession,
    test_university: University,
    second_university: University,
) -> None:
    """Verify that a role assignment in University A grants no access in University B."""
    user = User(
        university_id=test_university.id,
        username=f"scoped_user_{uuid.uuid4().hex[:6]}",
        email=f"scoped_{uuid.uuid4().hex[:6]}@test.edu",
        password_hash=hash_password("ScopedPass123!"),
        status=UserStatus.ACTIVE.value,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Assign UNIVERSITY_ADMIN role in test_university
    role_res = await db_session.execute(
        select(Role).where(Role.code == SystemRole.UNIVERSITY_ADMIN.value)
    )
    admin_role = role_res.scalar_one()

    await RbacService.assign_role(
        db_session,
        user_id=user.id,
        role_id=admin_role.id,
        university_id=test_university.id,
        assigned_by=None,
        scope_type=ScopeType.UNIVERSITY.value,
        scope_id=test_university.id,
    )
    await db_session.commit()

    # User has users:read in test_university
    has_test_perm = await RbacService.has_permission(
        db_session,
        user.id,
        PermissionCode.USERS_READ.value,
        test_university.id,
    )
    assert has_test_perm is True

    # User has NO permissions in second_university
    has_second_perm = await RbacService.has_permission(
        db_session,
        user.id,
        PermissionCode.USERS_READ.value,
        second_university.id,
    )
    assert has_second_perm is False


def test_rbac_api_endpoints_and_guards(
    client: TestClient,
    test_admin_user: User,
    test_university: University,
) -> None:
    """Verify API endpoints for roles and permissions with token authorization."""
    # Obtain token via real login flow
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_admin_user.username,
            "password": "SuperSecureAdmin123!",
            "university_id": str(test_university.id),
        },
    )
    assert login_res.status_code == 200
    admin_token = login_res.json()["data"]["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. GET /api/v1/roles with Super Admin token
    res = client.get("/api/v1/roles", headers=headers)
    assert res.status_code == 200
    roles_data = res.json()["data"]
    assert len(roles_data) >= 5
    role_codes = {r["code"] for r in roles_data}
    assert SystemRole.SUPER_ADMIN.value in role_codes

    # 2. GET /api/v1/permissions with Super Admin token
    res = client.get("/api/v1/permissions", headers=headers)
    assert res.status_code == 200
    perms_data = res.json()["data"]
    assert len(perms_data) >= 14

    # 3. Deny by default without authorization header
    res_unauth = client.get("/api/v1/roles")
    assert res_unauth.status_code == 401
