"""Integration tests for Milestone 14 Campus Network Zones management.

Invariants Tested:
- CIDR normalization and validation (IPv4 and IPv6).
- Unique zone code per university.
- Scoped to university tenant boundary.
- Active/disabled status toggling.
- Multi-tenant isolation between University A and University B.
"""

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


def test_campus_network_zone_crud_and_validation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify zone creation, IPv4/IPv6 normalization, code uniqueness, update, and deactivation."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]
    code_v4 = f"ZONE_ENG_{suffix}".upper()
    code_v6 = f"ZONE_V6_{suffix}".upper()

    # 1. Reject malformed CIDR
    bad_res = client.post(
        "/api/v1/security/network-zones",
        headers=headers,
        json={
            "name": "Bad Zone",
            "code": f"ZONE_BAD_{suffix}",
            "network_cidr": "invalid-cidr-string",
        },
    )
    assert bad_res.status_code == 400
    assert bad_res.json()["error"]["code"] == "INVALID_CIDR_FORMAT"

    # 2. Create valid IPv4 zone
    res_v4 = client.post(
        "/api/v1/security/network-zones",
        headers=headers,
        json={
            "name": "Engineering Wi-Fi",
            "code": code_v4,
            "network_cidr": "192.168.1.5/24",  # Should normalize host bits to 192.168.1.0/24
            "zone_type": "CAMPUS_TRUSTED",
            "priority": 100,
            "allow_student_presence": True,
        },
    )
    assert res_v4.status_code == 201
    v4_data = res_v4.json()["data"]
    zone_id = v4_data["id"]
    assert v4_data["code"] == code_v4
    assert v4_data["network_cidr"] == "192.168.1.0/24"
    assert v4_data["ip_version"] == 4
    assert v4_data["status"] == "ACTIVE"

    # 3. Create valid IPv6 zone
    res_v6 = client.post(
        "/api/v1/security/network-zones",
        headers=headers,
        json={
            "name": "Campus IPv6 Subnet",
            "code": code_v6,
            "network_cidr": "2001:db8:acad::/48",
            "zone_type": "CAMPUS_TRUSTED",
            "priority": 80,
        },
    )
    assert res_v6.status_code == 201
    v6_data = res_v6.json()["data"]
    assert v6_data["ip_version"] == 6
    assert v6_data["network_cidr"] == "2001:db8:acad::/48"

    # 4. Reject duplicate code in same university
    dup_res = client.post(
        "/api/v1/security/network-zones",
        headers=headers,
        json={
            "name": "Duplicate Zone",
            "code": code_v4,
            "network_cidr": "10.0.0.0/16",
        },
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "NETWORK_ZONE_CODE_EXISTS"

    # 5. List zones
    list_res = client.get("/api/v1/security/network-zones", headers=headers)
    assert list_res.status_code == 200
    zones = list_res.json()["data"]
    assert any(z["id"] == zone_id for z in zones)

    # 6. Update zone
    patch_res = client.patch(
        f"/api/v1/security/network-zones/{zone_id}",
        headers=headers,
        json={
            "name": "Updated Engineering Wi-Fi",
            "priority": 150,
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["name"] == "Updated Engineering Wi-Fi"
    assert patch_res.json()["data"]["priority"] == 150

    # 7. Disable zone
    del_res = client.delete(f"/api/v1/security/network-zones/{zone_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["data"]["status"] == "DISABLED"


@pytest.mark.asyncio
async def test_campus_network_zone_tenant_isolation(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
    second_university: University,
    test_admin_user: User,
) -> None:
    """Verify that zones belonging to University A cannot be read or modified by University B."""
    headers_a = get_admin_headers(client, test_admin_user, test_university)

    # Create zone in University A
    res = client.post(
        "/api/v1/security/network-zones",
        headers=headers_a,
        json={
            "name": "Univ A Zone",
            "code": f"UNIV_A_{uuid.uuid4().hex[:6]}".upper(),
            "network_cidr": "10.10.0.0/16",
        },
    )
    assert res.status_code == 201
    zone_a_id = res.json()["data"]["id"]

    # Create admin user in University B
    suffix_b = uuid.uuid4().hex[:6]
    admin_b = User(
        university_id=second_university.id,
        username=f"admin_b_{suffix_b}",
        email=f"admin_b_{suffix_b}@univ-b.edu",
        password_hash=hash_password("AdminSecure123!"),
        status=UserStatus.ACTIVE.value,
        must_change_password=False,
    )
    db_session.add(admin_b)
    await db_session.flush()

    role_stmt = select(Role).where(Role.code == SystemRole.UNIVERSITY_ADMIN.value)
    role_b = (await db_session.execute(role_stmt)).scalar_one()
    await RbacService.assign_role(
        db=db_session,
        user_id=admin_b.id,
        role_id=role_b.id,
        university_id=second_university.id,
        assigned_by=test_admin_user.id,
        scope_type=ScopeType.UNIVERSITY.value,
        scope_id=second_university.id,
    )

    # Login as Admin B
    login_b = client.post(
        "/api/v1/auth/login",
        json={
            "username": admin_b.username,
            "password": "AdminSecure123!",
            "university_id": str(second_university.id),
        },
    )
    assert login_b.status_code == 200
    token_b = login_b.json()["data"]["tokens"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Admin B attempts to read University A's zone -> must be 404
    get_res = client.get(f"/api/v1/security/network-zones/{zone_a_id}", headers=headers_b)
    assert get_res.status_code == 404

    # Admin B attempts to update University A's zone -> must be 404
    patch_res = client.patch(
        f"/api/v1/security/network-zones/{zone_a_id}",
        headers=headers_b,
        json={"name": "Hijacked Zone"},
    )
    assert patch_res.status_code == 404

    # University B listing must NOT include University A's zone
    list_b = client.get("/api/v1/security/network-zones", headers=headers_b)
    assert list_b.status_code == 200
    assert not any(z["id"] == zone_a_id for z in list_b.json()["data"])
