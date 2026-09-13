"""Test suite for scoped RBAC authorization across academic unit hierarchies and tenants."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.passwords import hash_password
from backend.app.core.constants import ScopeType, SystemRole, UserStatus
from backend.app.models.role import Role
from backend.app.models.university import University
from backend.app.models.user import User
from backend.app.rbac.service import RbacService
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_faculty_admin_subtree_authority_and_sibling_isolation(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Faculty Admin has subtree authority and is denied sibling faculties."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # 1. Create Faculty X and Faculty Y (siblings)
    fac_x_res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={"name": "Engineering Faculty", "code": f"ENG_{suffix}", "unit_type": "FACULTY"},
    )
    fac_x_id = uuid.UUID(fac_x_res.json()["data"]["id"])

    fac_y_res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={"name": "Medicine Faculty", "code": f"MED_{suffix}", "unit_type": "FACULTY"},
    )
    fac_y_id = uuid.UUID(fac_y_res.json()["data"]["id"])

    # 2. Create Department X1 under Faculty X, and Department Y1 under Faculty Y
    dept_x1_res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": "Software Dept",
            "code": f"SW_{suffix}",
            "unit_type": "DEPARTMENT",
            "parent_id": str(fac_x_id),
        },
    )
    dept_x1_id = uuid.UUID(dept_x1_res.json()["data"]["id"])

    dept_y1_res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={
            "name": "Surgery Dept",
            "code": f"SURG_{suffix}",
            "unit_type": "DEPARTMENT",
            "parent_id": str(fac_y_id),
        },
    )
    dept_y1_id = uuid.UUID(dept_y1_res.json()["data"]["id"])

    # 3. Create a dedicated Faculty Admin user scoped to Faculty X
    user_fac_admin = User(
        university_id=test_university.id,
        username=f"fac_admin_{suffix}",
        email=f"fac_admin_{suffix}@test.edu",
        password_hash=hash_password("FacAdminSecure123!"),
        status=UserStatus.ACTIVE.value,
        must_change_password=False,
    )
    db_session.add(user_fac_admin)
    await db_session.flush()

    # Find UNIVERSITY_ADMIN role (or create custom assignment)
    # We assign UNIVERSITY_ADMIN or role with academic_units.manage scoped to Faculty X
    role_stmt = select(Role).where(Role.code == SystemRole.UNIVERSITY_ADMIN.value)
    role_res = await db_session.execute(role_stmt)
    admin_role = role_res.scalar_one()

    # Assign role scoped to Faculty X
    await RbacService.assign_role(
        db=db_session,
        user_id=user_fac_admin.id,
        role_id=admin_role.id,
        university_id=test_university.id,
        assigned_by=test_admin_user.id,
        scope_type=ScopeType.ACADEMIC_UNIT.value,
        scope_id=fac_x_id,
    )

    # 4. Log in as fac_admin
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "username": user_fac_admin.username,
            "password": "FacAdminSecure123!",
            "university_id": str(test_university.id),
        },
    )
    assert login_res.status_code == 200
    fac_token = login_res.json()["data"]["tokens"]["access_token"]
    fac_headers = {"Authorization": f"Bearer {fac_token}"}

    # 5. fac_admin can update child department under Faculty X (Subtree authority)
    update_x_res = client.patch(
        f"/api/v1/academic-units/{dept_x1_id}",
        headers=fac_headers,
        json={"short_name": "SWE"},
    )
    assert update_x_res.status_code == 200
    assert update_x_res.json()["data"]["short_name"] == "SWE"

    # 6. fac_admin CANNOT update sibling department under Faculty Y (Sibling isolation)
    update_y_res = client.patch(
        f"/api/v1/academic-units/{dept_y1_id}",
        headers=fac_headers,
        json={"short_name": "SURG"},
    )
    assert update_y_res.status_code == 403
    assert update_y_res.json()["error"]["code"] == "PERMISSION_DENIED"

    # 7. fac_admin CANNOT move sibling department under Faculty Y
    move_y_res = client.post(
        f"/api/v1/academic-units/{dept_y1_id}/move",
        headers=fac_headers,
        json={"parent_id": None},
    )
    assert move_y_res.status_code == 403
    assert move_y_res.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_auditor_read_only_access(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify that AUDITOR role has read-only access and cannot execute mutations."""
    suffix = uuid.uuid4().hex[:6]

    # Create Auditor user
    auditor_user = User(
        university_id=test_university.id,
        username=f"auditor_{suffix}",
        email=f"auditor_{suffix}@test.edu",
        password_hash=hash_password("AuditorSecure123!"),
        status=UserStatus.ACTIVE.value,
        must_change_password=False,
    )
    db_session.add(auditor_user)
    await db_session.flush()

    # Assign AUDITOR role at university scope
    auditor_role_stmt = select(Role).where(Role.code == SystemRole.AUDITOR.value)
    auditor_role = (await db_session.execute(auditor_role_stmt)).scalar_one()

    await RbacService.assign_role(
        db=db_session,
        user_id=auditor_user.id,
        role_id=auditor_role.id,
        university_id=test_university.id,
        assigned_by=test_admin_user.id,
        scope_type=ScopeType.UNIVERSITY.value,
        scope_id=test_university.id,
    )

    # Log in as auditor
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "username": auditor_user.username,
            "password": "AuditorSecure123!",
            "university_id": str(test_university.id),
        },
    )
    assert login_res.status_code == 200
    token = login_res.json()["data"]["tokens"]["access_token"]
    aud_headers = {"Authorization": f"Bearer {token}"}

    # Auditor CAN read academic units
    list_res = client.get("/api/v1/academic-units", headers=aud_headers)
    assert list_res.status_code == 200

    # Auditor CANNOT create academic units
    create_res = client.post(
        "/api/v1/academic-units",
        headers=aud_headers,
        json={"name": "Unauthorized Faculty", "code": f"UNAUTH_{suffix}", "unit_type": "FACULTY"},
    )
    assert create_res.status_code == 403
    assert create_res.json()["error"]["code"] == "PERMISSION_DENIED"
