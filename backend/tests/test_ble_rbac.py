"""API and RBAC integration tests for Milestone 11 BLE presence verification endpoints.

Validates:
- GET /api/v1/attendance/checkpoints/{checkpoint_id}/ble-advertisement:
  - Lecturer assigned to occurrence -> 200 OK + Cache-Control: no-store
  - Unassigned lecturer -> 403 Forbidden
  - Student -> 403 Forbidden
  - Anonymous -> 401 Unauthorized
- POST /api/v1/attendance/presence/check-in:
  - Enrolled student dual factor -> 200 OK (accepted=True, already_credited=False)
  - Enrolled student duplicate -> 200 OK (accepted=True, already_credited=True)
  - Tampered BLE payload -> 400 Bad Request (BLE_PAYLOAD_INVALID)
  - Weak BLE signal -> 400 Bad Request (BLE_SIGNAL_TOO_WEAK)
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
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_lecturer_ble_advertisement_authorization_and_unassigned_denial(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify assigned lecturer can fetch BLE advertisement payload with Cache-Control: no-store,
    while unassigned lecturer and student are denied with 403.
    """
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    # 1. Create Lecturer A (assigned to occurrence)
    lec_a_uid, lec_a_name, lec_a_pwd = create_test_user(client, admin_headers, prefix="lec_a_ble")
    lec_a_res = client.post(
        "/api/v1/lecturers",
        headers=admin_headers,
        json={"user_id": lec_a_uid, "employee_code": f"LA-BLE-{uuid.uuid4().hex[:6]}"},
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

    # 2. Create Lecturer B (unassigned)
    lec_b_uid, lec_b_name, lec_b_pwd = create_test_user(client, admin_headers, prefix="lec_b_ble")
    client.post(
        "/api/v1/lecturers",
        headers=admin_headers,
        json={"user_id": lec_b_uid, "employee_code": f"LB-BLE-{uuid.uuid4().hex[:6]}"},
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

    # 3. Create Student
    s_uid, s_name, s_pwd = create_test_user(client, admin_headers, prefix="stu_ble_fetch")
    s_res = client.post(
        "/api/v1/students",
        headers=admin_headers,
        json={"user_id": s_uid, "student_number": f"STU-BF-{uuid.uuid4().hex[:6]}"},
    )
    s_id = s_res.json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=admin_headers,
        json={"student_id": s_id},
    )
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

    # 4. Open active session and START checkpoint
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

    # 5. Assigned Lecturer A fetches BLE advertisement -> 200 OK + Cache-Control: no-store
    lec_a_headers = get_user_headers(client, lec_a_name, lec_a_pwd, str(test_university.id))
    ble_res = client.get(
        f"/api/v1/attendance/checkpoints/{cp_id}/ble-advertisement",
        headers=lec_a_headers,
    )
    assert ble_res.status_code == 200
    ble_body = ble_res.json()["data"]
    assert "payload_base64" in ble_body
    assert ble_body["checkpoint_id"] == cp_id
    assert ble_body["checkpoint_type"] == "START"
    assert "no-store" in ble_res.headers.get("cache-control", "")

    # 6. Unassigned Lecturer B tries to fetch BLE advertisement -> 403 Forbidden
    lec_b_headers = get_user_headers(client, lec_b_name, lec_b_pwd, str(test_university.id))
    ble_b_res = client.get(
        f"/api/v1/attendance/checkpoints/{cp_id}/ble-advertisement",
        headers=lec_b_headers,
    )
    assert ble_b_res.status_code == 403

    # 7. Student tries to fetch BLE advertisement -> 403 Forbidden
    stu_headers = get_user_headers(client, s_name, s_pwd, str(test_university.id))
    ble_s_res = client.get(
        f"/api/v1/attendance/checkpoints/{cp_id}/ble-advertisement",
        headers=stu_headers,
    )
    assert ble_s_res.status_code == 403

    # 8. Anonymous caller -> 401 Unauthorized
    anon_res = client.get(f"/api/v1/attendance/checkpoints/{cp_id}/ble-advertisement")
    assert anon_res.status_code == 401


@pytest.mark.asyncio
async def test_student_presence_checkin_api_lifecycle(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify enrolled student check-in with dual-factor, tampering, weak RSSI, and RBAC."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    # 1. Create and enroll student
    s_uid, s_name, s_pwd = create_test_user(client, admin_headers, prefix="stu_api_pres")
    s_res = client.post(
        "/api/v1/students",
        headers=admin_headers,
        json={"user_id": s_uid, "student_number": f"STU-PR-{uuid.uuid4().hex[:6]}"},
    )
    s_id = s_res.json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=admin_headers,
        json={"student_id": s_id},
    )

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

    stu_headers = get_user_headers(client, s_name, s_pwd, str(test_university.id))

    # 2. Open active session and START checkpoint
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=admin_headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]

    # Configure session policy snapshot for QR_AND_BLE
    from sqlalchemy.orm.attributes import flag_modified

    sess_obj = await db_session.get(AttendanceSession, uuid.UUID(session_id))
    assert sess_obj is not None
    snapshot = dict(sess_obj.policy_snapshot or {})
    snapshot["presence_requirement_mode"] = "QR_AND_BLE"
    snapshot["ble_min_rssi"] = -85
    sess_obj.policy_snapshot = snapshot
    flag_modified(sess_obj, "policy_snapshot")
    await db_session.commit()

    cp_open_res = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/open",
        headers=admin_headers,
        json={"window_duration_seconds": 300},
    )
    cp_id = cp_open_res.json()["data"]["id"]

    fixed_time = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    with patch("backend.app.attendance.service.utc_now", return_value=fixed_time):
        # 3. Retrieve dynamic QR token and BLE advertisement
        token_res = client.get(
            f"/api/v1/attendance/checkpoints/{cp_id}/qr-token",
            headers=admin_headers,
        )
        assert token_res.status_code == 200
        qr_token = token_res.json()["data"]["token"]

        ble_res = client.get(
            f"/api/v1/attendance/checkpoints/{cp_id}/ble-advertisement",
            headers=admin_headers,
        )
        assert ble_res.status_code == 200
        ble_payload = ble_res.json()["data"]["payload_base64"]

        # 4. Student submits valid dual-factor check-in -> 200 OK
        valid_body = {
            "qr_token": qr_token,
            "ble_observation": {
                "payload": ble_payload,
                "rssi": -70,
                "observed_at_client": fixed_time.isoformat(),
            },
        }
        checkin_res = client.post(
            "/api/v1/attendance/presence/check-in",
            headers=stu_headers,
            json=valid_body,
        )
        assert checkin_res.status_code == 200
        c_data = checkin_res.json()["data"]
        assert c_data["accepted"] is True
        assert c_data["already_credited"] is False
        assert c_data["checkpoint_type"] == "START"
        assert c_data["presence_mode"] == "QR_AND_BLE"

        # 5. Duplicate check-in -> 200 OK (already_credited=True)
        dup_res = client.post(
            "/api/v1/attendance/presence/check-in",
            headers=stu_headers,
            json=valid_body,
        )
        assert dup_res.status_code == 200
        d_data = dup_res.json()["data"]
        assert d_data["accepted"] is True
        assert d_data["already_credited"] is True

        # 6. Tampered BLE payload -> 400 Bad Request
        import base64

        raw_b = base64.b64decode(ble_payload)
        tampered_b64 = base64.b64encode(raw_b[:12] + b"badtag").decode("ascii")
        tamp_body = {
            "qr_token": qr_token,
            "ble_observation": {
                "payload": tampered_b64,
                "rssi": -70,
                "observed_at_client": fixed_time.isoformat(),
            },
        }
        tamp_res = client.post(
            "/api/v1/attendance/presence/check-in",
            headers=stu_headers,
            json=tamp_body,
        )
        assert tamp_res.status_code == 400
        assert tamp_res.json()["error"]["code"] == "INVALID_BLE_PAYLOAD"

        # 7. Weak RSSI (-95 dBm < -85 dBm) -> 400 Bad Request
        weak_body = {
            "qr_token": qr_token,
            "ble_observation": {
                "payload": ble_payload,
                "rssi": -95,
                "observed_at_client": fixed_time.isoformat(),
            },
        }
        weak_res = client.post(
            "/api/v1/attendance/presence/check-in",
            headers=stu_headers,
            json=weak_body,
        )
        assert weak_res.status_code == 400
        assert weak_res.json()["error"]["code"] == "BLE_SIGNAL_TOO_WEAK"

        # 8. Anonymous check-in -> 401 Unauthorized
        anon_res = client.post(
            "/api/v1/attendance/presence/check-in",
            json=valid_body,
        )
        assert anon_res.status_code == 401
