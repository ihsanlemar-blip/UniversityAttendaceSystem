"""RBAC and Multi-Tenant Isolation Tests for Milestone 14 Security Endpoints.

Invariants Tested:
- security.network_zones.manage:
    - University Admin can manage zones.
    - Student, Lecturer, Auditor receive 403 Forbidden.
- security.risk_signals.read:
    - University Admin and Auditor can read risk signals.
    - Student, Lecturer receive 403 Forbidden.
- security.risk_signals.review:
    - University Admin can review (acknowledge, resolve, dismiss).
    - Auditor receives 403 Forbidden (Auditor is strictly read-only).
    - Student, Lecturer receive 403 Forbidden.
- security.radio_analysis.read:
    - University Admin and Auditor can read radio diagnostics.
    - Student, Lecturer receive 403 Forbidden.
- Multi-Tenant Boundary Isolation:
    - University B Admin cannot view, modify, or review University A's zones or risk signals.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import (
    NetworkZoneType,
    RiskSeverity,
    RiskSignalType,
    RiskSubjectType,
    ScopeType,
    SystemRole,
)
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.university import University
from backend.app.models.user import User
from backend.app.security.risk_service import AntiCheatService
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_users import get_admin_headers


async def _setup_user_with_role(
    client: TestClient,
    admin_headers: dict[str, str],
    university: University,
    db_session: AsyncSession,
    role_code: str,
    prefix: str,
) -> tuple[User, dict[str, str]]:
    """Helper to create a user and assign a specific system role within a university."""
    u_id, username, password = create_test_user(client, admin_headers, prefix=prefix)
    user = await db_session.get(User, uuid.UUID(u_id))
    assert user is not None

    role_res = await db_session.execute(select(Role).where(Role.code == role_code))
    role = role_res.scalar_one()

    db_session.add(
        RoleAssignment(
            user_id=user.id,
            role_id=role.id,
            university_id=university.id,
            scope_type=ScopeType.UNIVERSITY.value,
            scope_id=university.id,
        )
    )
    await db_session.commit()

    headers = get_user_headers(client, username, password, str(university.id))
    return user, headers


def test_security_endpoints_unauthenticated(client: TestClient) -> None:
    """Verify unauthenticated requests to all security endpoints receive 401."""
    assert client.get("/api/v1/security/network-zones").status_code == 401
    assert client.post("/api/v1/security/network-zones", json={}).status_code == 401
    assert client.get("/api/v1/security/risk-signals").status_code == 401
    assert client.get("/api/v1/security/radio-analysis").status_code == 401


@pytest.mark.asyncio
async def test_security_network_zones_rbac(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify zone management RBAC matrix: Admin succeeds; Student, Lecturer, Auditor get 403."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)

    _, student_headers = await _setup_user_with_role(
        client, admin_headers, test_university, db_session, SystemRole.STUDENT.value, "sec_stu"
    )
    _, lecturer_headers = await _setup_user_with_role(
        client, admin_headers, test_university, db_session, SystemRole.LECTURER.value, "sec_lec"
    )
    _, auditor_headers = await _setup_user_with_role(
        client, admin_headers, test_university, db_session, SystemRole.AUDITOR.value, "sec_aud"
    )

    zone_payload = {
        "name": "Engineering Wi-Fi Zone",
        "code": f"ENG_WIFI_{uuid.uuid4().hex[:6]}".upper(),
        "network_cidr": "10.100.0.0/16",
        "zone_type": NetworkZoneType.CAMPUS_TRUSTED.value,
        "priority": 50,
        "allow_student_presence": True,
    }

    # 1. Student receives 403
    res_stu = client.post(
        "/api/v1/security/network-zones",
        headers=student_headers,
        json=zone_payload,
    )
    assert res_stu.status_code == 403

    # 2. Lecturer receives 403
    res_lec = client.post(
        "/api/v1/security/network-zones",
        headers=lecturer_headers,
        json=zone_payload,
    )
    assert res_lec.status_code == 403

    # 3. Auditor receives 403
    res_aud = client.post(
        "/api/v1/security/network-zones",
        headers=auditor_headers,
        json=zone_payload,
    )
    assert res_aud.status_code == 403

    # 4. Admin succeeds (201 Created)
    res_admin = client.post(
        "/api/v1/security/network-zones",
        headers=admin_headers,
        json=zone_payload,
    )
    assert res_admin.status_code == 201
    zone_id = res_admin.json()["data"]["id"]

    # 5. List zones: Admin succeeds, others 403
    assert client.get("/api/v1/security/network-zones", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/security/network-zones", headers=student_headers).status_code == 403
    assert client.get("/api/v1/security/network-zones", headers=lecturer_headers).status_code == 403
    assert client.get("/api/v1/security/network-zones", headers=auditor_headers).status_code == 403

    # 6. Patch zone: Admin succeeds, others 403
    assert (
        client.patch(
            f"/api/v1/security/network-zones/{zone_id}",
            headers=admin_headers,
            json={"priority": 80},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/security/network-zones/{zone_id}",
            headers=auditor_headers,
            json={"priority": 90},
        ).status_code
        == 403
    )


@pytest.mark.asyncio
async def test_security_risk_signals_rbac(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify risk signal read and review RBAC.

    Auditor can read but cannot review; Admin can both.
    """
    admin_headers = get_admin_headers(client, test_admin_user, test_university)

    student_user, student_headers = await _setup_user_with_role(
        client, admin_headers, test_university, db_session, SystemRole.STUDENT.value, "sig_stu"
    )
    _, lecturer_headers = await _setup_user_with_role(
        client, admin_headers, test_university, db_session, SystemRole.LECTURER.value, "sig_lec"
    )
    _, auditor_headers = await _setup_user_with_role(
        client, admin_headers, test_university, db_session, SystemRole.AUDITOR.value, "sig_aud"
    )

    # Seed a risk signal
    sig = await AntiCheatService.record_risk_signal(
        db=db_session,
        university_id=test_university.id,
        signal_type=RiskSignalType.STUDENT_OVERLAPPING_ATTENDANCE.value,
        severity=RiskSeverity.MEDIUM.value,
        risk_points=35,
        subject_type=RiskSubjectType.STUDENT.value,
        risk_key=f"SIG_RBAC:{test_university.id}:{uuid.uuid4().hex[:8]}",
        subject_user_id=student_user.id,
        context={"rule": "OVERLAPPING_ATTENDANCE", "observed": "test"},
    )
    await db_session.commit()
    sig_id = str(sig.id)

    # 1. Reading signals: Admin and Auditor get 200; Student and Lecturer get 403
    assert client.get("/api/v1/security/risk-signals", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/security/risk-signals", headers=auditor_headers).status_code == 200
    assert client.get("/api/v1/security/risk-signals", headers=student_headers).status_code == 403
    assert client.get("/api/v1/security/risk-signals", headers=lecturer_headers).status_code == 403

    # 2. Detail read
    assert (
        client.get(f"/api/v1/security/risk-signals/{sig_id}", headers=admin_headers).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/security/risk-signals/{sig_id}", headers=auditor_headers).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/security/risk-signals/{sig_id}", headers=student_headers).status_code
        == 403
    )

    # 3. Review actions (Acknowledge / Resolve / Dismiss):
    # Auditor gets 403 Forbidden (Auditor cannot review)
    res_aud_ack = client.post(
        f"/api/v1/security/risk-signals/{sig_id}/acknowledge",
        headers=auditor_headers,
    )
    assert res_aud_ack.status_code == 403

    res_aud_res = client.post(
        f"/api/v1/security/risk-signals/{sig_id}/resolve",
        headers=auditor_headers,
        json={"review_note": "Auditor attempting resolution"},
    )
    assert res_aud_res.status_code == 403

    # Student and Lecturer get 403 Forbidden
    assert (
        client.post(
            f"/api/v1/security/risk-signals/{sig_id}/acknowledge",
            headers=student_headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/security/risk-signals/{sig_id}/acknowledge",
            headers=lecturer_headers,
        ).status_code
        == 403
    )

    # Admin successfully acknowledges and resolves
    res_adm_ack = client.post(
        f"/api/v1/security/risk-signals/{sig_id}/acknowledge",
        headers=admin_headers,
    )
    assert res_adm_ack.status_code == 200
    assert res_adm_ack.json()["data"]["status"] == "ACKNOWLEDGED"

    res_adm_res = client.post(
        f"/api/v1/security/risk-signals/{sig_id}/resolve",
        headers=admin_headers,
        json={"review_note": "Resolved after review of classroom logs."},
    )
    assert res_adm_res.status_code == 200
    assert res_adm_res.json()["data"]["status"] == "RESOLVED"


@pytest.mark.asyncio
async def test_security_radio_analysis_rbac(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify radio diagnostics read RBAC.

    Admin and Auditor get 200; Student and Lecturer get 403.
    """
    admin_headers = get_admin_headers(client, test_admin_user, test_university)

    _, student_headers = await _setup_user_with_role(
        client, admin_headers, test_university, db_session, SystemRole.STUDENT.value, "rad_stu"
    )
    _, lecturer_headers = await _setup_user_with_role(
        client, admin_headers, test_university, db_session, SystemRole.LECTURER.value, "rad_lec"
    )
    _, auditor_headers = await _setup_user_with_role(
        client, admin_headers, test_university, db_session, SystemRole.AUDITOR.value, "rad_aud"
    )

    assert client.get("/api/v1/security/radio-analysis", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/security/radio-analysis", headers=auditor_headers).status_code == 200
    assert client.get("/api/v1/security/radio-analysis", headers=student_headers).status_code == 403
    res_rad_lec = client.get("/api/v1/security/radio-analysis", headers=lecturer_headers)
    assert res_rad_lec.status_code == 403


@pytest.mark.asyncio
async def test_security_cross_tenant_isolation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    second_university: University,
    second_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify University B admin cannot view, patch, or resolve University A's resources."""
    headers_a = get_admin_headers(client, test_admin_user, test_university)
    headers_b = get_admin_headers(client, second_admin_user, second_university)

    # 1. Create Zone in University A
    res_zone_a = client.post(
        "/api/v1/security/network-zones",
        headers=headers_a,
        json={
            "name": "Uni A CS Lab Zone",
            "code": f"UNI_A_CS_{uuid.uuid4().hex[:6]}".upper(),
            "network_cidr": "10.10.0.0/16",
            "zone_type": NetworkZoneType.CAMPUS_TRUSTED.value,
        },
    )
    assert res_zone_a.status_code == 201
    zone_a_id = res_zone_a.json()["data"]["id"]

    # 2. Uni B listing zones must not contain Zone A
    res_list_b = client.get("/api/v1/security/network-zones", headers=headers_b)
    assert res_list_b.status_code == 200
    zone_ids_b = [z["id"] for z in res_list_b.json()["data"]]
    assert zone_a_id not in zone_ids_b

    # 3. Uni B attempting to patch Zone A receives 404
    res_patch_cross = client.patch(
        f"/api/v1/security/network-zones/{zone_a_id}",
        headers=headers_b,
        json={"name": "Hijacked Zone Name"},
    )
    assert res_patch_cross.status_code == 404

    # 4. Create Risk Signal in University A
    sig_a = await AntiCheatService.record_risk_signal(
        db=db_session,
        university_id=test_university.id,
        signal_type=RiskSignalType.SESSION_OUTSIDE_SCHEDULE_WINDOW.value,
        severity=RiskSeverity.HIGH.value,
        risk_points=50,
        subject_type=RiskSubjectType.LECTURER.value,
        risk_key=f"SIG_TENANT_A:{test_university.id}:{uuid.uuid4().hex[:8]}",
        context={"rule": "SESSION_OUTSIDE_SCHEDULE_WINDOW"},
    )
    await db_session.commit()
    sig_a_id = str(sig_a.id)

    # 5. Uni B listing risk signals must not contain Signal A
    res_signals_b = client.get("/api/v1/security/risk-signals", headers=headers_b)
    assert res_signals_b.status_code == 200
    signal_ids_b = [s["id"] for s in res_signals_b.json()["data"]]
    assert sig_a_id not in signal_ids_b

    # 6. Uni B attempting to get detail or resolve Signal A receives 404
    detail_res = client.get(f"/api/v1/security/risk-signals/{sig_a_id}", headers=headers_b)
    assert detail_res.status_code == 404
    assert (
        client.post(
            f"/api/v1/security/risk-signals/{sig_a_id}/resolve",
            headers=headers_b,
            json={"review_note": "Cross-tenant resolve attempt"},
        ).status_code
        == 404
    )
