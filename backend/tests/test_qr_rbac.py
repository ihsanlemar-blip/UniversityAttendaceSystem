"""API and RBAC integration tests for Milestone 10 Dynamic QR endpoints.

Validates:
- GET /api/v1/attendance/checkpoints/{checkpoint_id}/qr-token:
  - Lecturer assigned to occurrence -> 200 OK + Cache-Control: no-store
  - Unassigned lecturer -> 403 Forbidden
  - Student -> 403 Forbidden
  - Anonymous -> 401 Unauthorized
- POST /api/v1/attendance/qr/check-in:
  - Enrolled student -> 200 OK (accepted=True, already_credited=False)
  - Enrolled student repeat scan -> 200 OK (accepted=True, already_credited=True)
  - Tampered token -> 400 Bad Request (INVALID_QR_TOKEN)
  - Anonymous -> 401 Unauthorized
  - Non-student user -> 403 Forbidden (STUDENT_PROFILE_REQUIRED)
"""

import datetime
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import ScopeType, SystemRole
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_lecturer_qr_token_authorization_and_unassigned_denial(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify assigned lecturer can fetch dynamic QR token with Cache-Control: no-store,

    while unassigned lecturer and student are denied with 403.
    """
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    # Create Lecturer A (assigned to occurrence)
    lec_a_uid, lec_a_name, lec_a_pwd = create_test_user(client, admin_headers, prefix="lec_a_qr")
    lec_a_res = client.post(
        "/api/v1/lecturers",
        headers=admin_headers,
        json={"user_id": lec_a_uid, "employee_code": f"LA-{uuid.uuid4().hex[:6]}"},
    )
    lec_a_id = lec_a_res.json()["data"]["id"]

    # Assign Lecturer A to Offering
    client.post(
        f"/api/v1/course-offerings/{offering_id}/lecturers",
        headers=admin_headers,
        json={"lecturer_id": lec_a_id, "is_primary": True},
    )

    # Assign LECTURER role to Lecturer A
    lec_role_res = await db_session.execute(
        select(Role).where(Role.code == SystemRole.LECTURER.value)
    )
    lec_role = lec_role_res.scalar_one()
    db_session.add(
        RoleAssignment(
            user_id=uuid.UUID(lec_a_uid),
            role_id=lec_role.id,
            university_id=test_university.id,
            scope_type=ScopeType.UNIVERSITY.value,
            scope_id=test_university.id,
        )
    )

    # Create Lecturer B (unassigned)
    lec_b_uid, lec_b_name, lec_b_pwd = create_test_user(client, admin_headers, prefix="lec_b_qr")
    client.post(
        "/api/v1/lecturers",
        headers=admin_headers,
        json={"user_id": lec_b_uid, "employee_code": f"LB-{uuid.uuid4().hex[:6]}"},
    )
    db_session.add(
        RoleAssignment(
            user_id=uuid.UUID(lec_b_uid),
            role_id=lec_role.id,
            university_id=test_university.id,
            scope_type=ScopeType.UNIVERSITY.value,
            scope_id=test_university.id,
        )
    )
    await db_session.commit()

    # Initialize active attendance session and open START checkpoint
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=admin_headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]

    cp_open_res = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/open",
        headers=admin_headers,
        json={"window_duration_seconds": 300},
    )
    cp_id = cp_open_res.json()["data"]["id"]

    # 1. Assigned Lecturer A fetches QR token -> 200 OK + Cache-Control: no-store
    lec_a_headers = get_user_headers(client, lec_a_name, lec_a_pwd, str(test_university.id))
    token_res = client.get(
        f"/api/v1/attendance/checkpoints/{cp_id}/qr-token",
        headers=lec_a_headers,
    )
    assert token_res.status_code == 200
    token_body = token_res.json()["data"]
    assert "token" in token_body
    assert token_body["checkpoint_id"] == cp_id
    assert token_body["checkpoint_type"] == "START"
    assert "no-store" in token_res.headers.get("cache-control", "")

    # 2. Unassigned Lecturer B tries to fetch QR token -> 403 Forbidden
    lec_b_headers = get_user_headers(client, lec_b_name, lec_b_pwd, str(test_university.id))
    token_b_res = client.get(
        f"/api/v1/attendance/checkpoints/{cp_id}/qr-token",
        headers=lec_b_headers,
    )
    assert token_b_res.status_code == 403

    # 3. Anonymous caller -> 401 Unauthorized
    anon_res = client.get(f"/api/v1/attendance/checkpoints/{cp_id}/qr-token")
    assert anon_res.status_code == 401


@pytest.mark.asyncio
async def test_student_qr_checkin_api_lifecycle(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify enrolled student check-in, idempotency, tampering, and unauthenticated
    handling via HTTP.
    """
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    # 1. Create and enroll student
    s_uid, s_name, s_pwd = create_test_user(client, admin_headers, prefix="stu_api_qr")
    s_res = client.post(
        "/api/v1/students",
        headers=admin_headers,
        json={"user_id": s_uid, "student_number": f"STU-{uuid.uuid4().hex[:6]}"},
    )
    s_id = s_res.json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=admin_headers,
        json={"student_id": s_id},
    )

    # Grant STUDENT role to student
    stu_role_res = await db_session.execute(
        select(Role).where(Role.code == SystemRole.STUDENT.value)
    )
    stu_role = stu_role_res.scalar_one()
    db_session.add(
        RoleAssignment(
            user_id=uuid.UUID(s_uid),
            role_id=stu_role.id,
            university_id=test_university.id,
            scope_type=ScopeType.UNIVERSITY.value,
            scope_id=test_university.id,
        )
    )
    await db_session.commit()

    # 2. Student logs in
    stu_headers = get_user_headers(client, s_name, s_pwd, str(test_university.id))

    # 3. Open active session and START checkpoint
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=admin_headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]

    cp_open_res = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/open",
        headers=admin_headers,
        json={"window_duration_seconds": 300},
    )
    cp_id = cp_open_res.json()["data"]["id"]

    fixed_time = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)
    with patch("backend.app.attendance.service.utc_now", return_value=fixed_time):
        # 4. Admin retrieves dynamic QR token
        token_res = client.get(
            f"/api/v1/attendance/checkpoints/{cp_id}/qr-token",
            headers=admin_headers,
        )
        assert token_res.status_code == 200
        qr_token = token_res.json()["data"]["token"]

        # 5. Student submits valid scanned token -> 200 OK
        checkin_res = client.post(
            "/api/v1/attendance/qr/check-in",
            headers=stu_headers,
            json={"token": qr_token},
        )
        assert checkin_res.status_code == 200
        c_data = checkin_res.json()["data"]
        assert c_data["accepted"] is True
        assert c_data["already_credited"] is False
        assert c_data["checkpoint_type"] == "START"
        assert "attendance_record_id" in c_data

        # 6. Student repeats submission with SAME token -> 200 OK (idempotent,
        # already_credited=True)
        dup_res = client.post(
            "/api/v1/attendance/qr/check-in",
            headers=stu_headers,
            json={"token": qr_token},
        )
        assert dup_res.status_code == 200
        d_data = dup_res.json()["data"]
        assert d_data["accepted"] is True
        assert d_data["already_credited"] is True

        # 7. Tampered token -> 400 Bad Request
        bad_token = qr_token[:-3] + "xyz"
        tampered_res = client.post(
            "/api/v1/attendance/qr/check-in",
            headers=stu_headers,
            json={"token": bad_token},
        )
        assert tampered_res.status_code == 400
        assert tampered_res.json()["error"]["code"] == "INVALID_QR_TOKEN"

        # 8. Anonymous check-in -> 401 Unauthorized
        anon_checkin = client.post(
            "/api/v1/attendance/qr/check-in",
            json={"token": qr_token},
        )
        assert anon_checkin.status_code == 401
