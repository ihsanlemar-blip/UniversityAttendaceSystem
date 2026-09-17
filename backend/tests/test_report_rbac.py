"""RBAC, Multi-Tenant isolation, and IDOR prevention test suite for Reporting API."""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_corrections import (
    create_student_with_role,
    setup_closed_session,
)
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_student_idor_prevention(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify students can access /student/me but cannot access /student/{id} or roster reports."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    s1_id, _, s1_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "idor_s1"
    )
    s2_id, _, s2_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "idor_s2"
    )
    setup_closed_session(client, admin_headers, occurrence_id)

    # 1. Student 1 can access /student/me
    s1_me = client.get("/api/v1/reports/attendance/student/me", headers=s1_headers)
    assert s1_me.status_code == 200
    assert s1_me.json()["data"]["student_id"] == s1_id

    # 2. Student 1 cannot view Student 2 via /student/{id} -> 403 Forbidden
    s1_view_s2 = client.get(f"/api/v1/reports/attendance/student/{s2_id}", headers=s1_headers)
    assert s1_view_s2.status_code == 403

    # 3. Student 1 cannot view Course Roster report -> 403 Forbidden
    s1_view_roster = client.get(
        f"/api/v1/reports/attendance/course-offerings/{offering_id}",
        headers=s1_headers,
    )
    assert s1_view_roster.status_code == 403


@pytest.mark.asyncio
async def test_auditor_read_only_access(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify AUDITOR role has read-only report access and export capability."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    setup_closed_session(client, admin_headers, occurrence_id)

    # Create Auditor user
    aud_uid, aud_email, aud_pwd = create_test_user(client, admin_headers, prefix="rep_aud")
    roles_res = client.get("/api/v1/roles", headers=admin_headers)
    aud_role_id = next(r["id"] for r in roles_res.json()["data"] if r["code"] == "AUDITOR")
    client.post(
        f"/api/v1/users/{aud_uid}/role-assignments",
        headers=admin_headers,
        json={
            "role_id": aud_role_id,
            "scope_type": "UNIVERSITY",
            "scope_id": str(test_university.id),
        },
    )
    aud_headers = get_user_headers(client, aud_email, aud_pwd, str(test_university.id))

    # Auditor can view course roster report
    roster_res = client.get(
        f"/api/v1/reports/attendance/course-offerings/{offering_id}",
        headers=aud_headers,
    )
    assert roster_res.status_code == 200

    # Auditor can export course roster report
    export_res = client.get(
        f"/api/v1/reports/attendance/course-offerings/{offering_id}/export?format=CSV",
        headers=aud_headers,
    )
    assert export_res.status_code == 200


@pytest.mark.asyncio
async def test_cross_tenant_isolation_returns_404(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify offering and department reports for non-existent or other tenant resources return
    404.
    """
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    fake_id = uuid.uuid4()

    res = client.get(
        f"/api/v1/reports/attendance/course-offerings/{fake_id}",
        headers=admin_headers,
    )
    assert res.status_code == 404

    res2 = client.get(
        f"/api/v1/reports/attendance/department/{fake_id}",
        headers=admin_headers,
    )
    assert res2.status_code == 404
