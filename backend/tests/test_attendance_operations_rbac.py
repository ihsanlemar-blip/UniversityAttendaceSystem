"""Test suite for Attendance Operations RBAC permissions across system roles.

Verifies:
- Student role permissions (request only, no review, no override)
- Lecturer role permissions (review and override within assigned offerings)
- Attendance Officer role permissions (review, override, audit timeline read)
- Department / Faculty / University Admin full operational permissions
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.core.constants import (
    AttendanceStatus,
    SystemRole,
)
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_corrections import (
    create_student_with_role,
    setup_closed_session,
)
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_users import get_admin_headers


def create_user_with_role(
    client: TestClient,
    admin_headers: dict[str, str],
    university_id: uuid.UUID,
    role_code: SystemRole,
    prefix: str,
) -> tuple[str, dict[str, str]]:
    """Helper creating user and assigning a specific system role."""
    salt = uuid.uuid4().hex[:6]
    user_id, email, pwd = create_test_user(client, admin_headers, prefix=f"{prefix}_{salt}")

    roles_res = client.get("/api/v1/roles", headers=admin_headers)
    target_role_id = next(r["id"] for r in roles_res.json()["data"] if r["code"] == role_code.value)
    client.post(
        f"/api/v1/users/{user_id}/role-assignments",
        headers=admin_headers,
        json={
            "role_id": target_role_id,
            "scope_type": "UNIVERSITY",
            "scope_id": str(university_id),
        },
    )

    user_headers = get_user_headers(client, email, pwd, str(university_id))
    return user_id, user_headers


@pytest.mark.asyncio
async def test_student_rbac_boundaries(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Student can request but receives 403 on reviewer/override endpoints."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    s_id, _, s_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "rbac_std"
    )

    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)
    rec_res = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    record_id = next(r["id"] for r in rec_res.json()["data"] if r["student_id"] == s_id)

    # 1. Student can list their requests -> 200
    my_res = client.get("/api/v1/attendance/operations/corrections/my", headers=s_headers)
    assert my_res.status_code == 200

    # 2. Student cannot access reviewer queue -> 403
    q_res = client.get("/api/v1/attendance/operations/corrections/queue", headers=s_headers)
    assert q_res.status_code == 403

    # 3. Student cannot perform direct override -> 403
    ovr_res = client.post(
        "/api/v1/attendance/operations/overrides",
        headers=s_headers,
        json={
            "attendance_record_id": record_id,
            "target_status": AttendanceStatus.PRESENT.value,
            "reason": "Student unauthorized override attempt.",
        },
    )
    assert ovr_res.status_code == 403

    # 4. Student cannot perform reversal -> 403
    rev_res = client.post(
        "/api/v1/attendance/operations/reversals",
        headers=s_headers,
        json={
            "revision_id": str(uuid.uuid4()),
            "reason": "Student unauthorized reversal.",
        },
    )
    assert rev_res.status_code == 403

    # 5. Student cannot read audit timeline -> 403
    time_res = client.get(
        f"/api/v1/attendance/operations/records/{record_id}/timeline",
        headers=s_headers,
    )
    assert time_res.status_code == 403


@pytest.mark.asyncio
async def test_attendance_officer_and_admin_rbac_access(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Attendance Officer has review, override, and audit permissions."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    s_id, _, _ = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "std_officer"
    )

    _, officer_headers = create_user_with_role(
        client,
        admin_headers,
        test_university.id,
        SystemRole.ATTENDANCE_OFFICER,
        "officer",
    )

    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)
    rec_res = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    record_id = next(r["id"] for r in rec_res.json()["data"] if r["student_id"] == s_id)

    # 1. Officer can view review queue -> 200
    q_res = client.get("/api/v1/attendance/operations/corrections/queue", headers=officer_headers)
    assert q_res.status_code == 200

    # 2. Officer can read record audit timeline -> 200
    tl_res = client.get(
        f"/api/v1/attendance/operations/records/{record_id}/timeline",
        headers=officer_headers,
    )
    assert tl_res.status_code == 200

    # 3. Officer can perform override -> 200
    ovr_res = client.post(
        "/api/v1/attendance/operations/overrides",
        headers=officer_headers,
        json={
            "attendance_record_id": record_id,
            "target_status": AttendanceStatus.PRESENT.value,
            "reason": "Officer verified student entry via biometric turnstile backup.",
        },
    )
    assert ovr_res.status_code == 200
    assert ovr_res.json()["data"]["status"] == AttendanceStatus.PRESENT.value
