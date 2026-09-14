"""Test suite for Attendance combinatorial 8-pattern evaluation engine and invariants.

Covers INV-01 (client cannot mark self present) and INV-05 (no duplicate credit).
"""

import uuid

from fastapi.testclient import TestClient

from backend.app.core.constants import AttendanceStatus
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_attendance_sessions import create_enrolled_student
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_users import get_admin_headers


def test_combinatorial_8_pattern_evaluation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify all 8 combinations of (START, MIDDLE, END) evaluate to the correct
    AttendanceStatus and credit.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)

    # Patterns: (start, middle, end) -> (expected_status, expected_credit)
    patterns = {
        "111": (True, True, True, AttendanceStatus.PRESENT.value, 1.0),
        "110": (True, True, False, AttendanceStatus.PRESENT.value, 1.0),
        "101": (True, False, True, AttendanceStatus.PRESENT.value, 1.0),
        "011": (False, True, True, AttendanceStatus.LATE.value, 0.5),
        "100": (True, False, False, AttendanceStatus.LATE.value, 0.5),
        "010": (False, True, False, AttendanceStatus.LATE.value, 0.5),
        "001": (False, False, True, AttendanceStatus.ABSENT.value, 0.0),
        "000": (False, False, False, AttendanceStatus.ABSENT.value, 0.0),
    }

    # 1. Enroll 8 students for the 8 patterns
    pattern_students: dict[str, str] = {}
    for code in patterns:
        sid = create_enrolled_student(client, headers, offering_id, f"pat_{code}")
        pattern_students[code] = sid

    # 2. Initialize and open session (freezes roster)
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["data"]["id"]

    # 3. Credit checkpoints per pattern
    for code, (has_start, has_mid, has_end, _, _) in patterns.items():
        sid = pattern_students[code]
        if has_start:
            res = client.post(
                f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/manual-credit",
                headers=headers,
                json={"student_id": sid, "reason": f"Credit START for pattern {code}"},
            )
            assert res.status_code == 200

        if has_mid:
            res = client.post(
                f"/api/v1/attendance/sessions/{session_id}/checkpoints/MIDDLE/manual-credit",
                headers=headers,
                json={"student_id": sid, "reason": f"Credit MIDDLE for pattern {code}"},
            )
            assert res.status_code == 200

        if has_end:
            res = client.post(
                f"/api/v1/attendance/sessions/{session_id}/checkpoints/END/manual-credit",
                headers=headers,
                json={"student_id": sid, "reason": f"Credit END for pattern {code}"},
            )
            assert res.status_code == 200

    # 4. Close session to execute combinatorial 8-pattern evaluation
    close_res = client.post(f"/api/v1/attendance/sessions/{session_id}/close", headers=headers)
    assert close_res.status_code == 200
    assert close_res.json()["data"]["status"] == "CLOSED"

    # 5. Verify records against expected evaluations
    rec_res = client.get(f"/api/v1/attendance/sessions/{session_id}/records", headers=headers)
    assert rec_res.status_code == 200
    records = rec_res.json()["data"]
    records_by_student = {r["student_id"]: r for r in records}

    for code, (has_start, has_mid, has_end, exp_status, exp_credit) in patterns.items():
        sid = pattern_students[code]
        r = records_by_student[sid]
        assert r["status"] == exp_status, (
            f"Failed for pattern {code}: expected {exp_status}, got {r['status']}"
        )
        assert r["attendance_credit"] == exp_credit, (
            f"Failed credit for {code}: expected {exp_credit}, got {r['attendance_credit']}"
        )
        assert r["start_credited"] is has_start
        assert r["middle_credited"] is has_mid
        assert r["end_credited"] is has_end
        assert r["calculation_snapshot"]["pattern"] == code
        assert r["finalized_at_utc"] is not None


def test_status_preservation_for_excused_and_leave(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify EXCUSED and LEAVE administrative statuses are preserved when session is closed."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)

    s_excused = create_enrolled_student(client, headers, offering_id, "excused")
    s_leave = create_enrolled_student(client, headers, offering_id, "leave")

    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]

    # Retrieve records to find record IDs
    rec_res = client.get(f"/api/v1/attendance/sessions/{session_id}/records", headers=headers)
    records = {r["student_id"]: r["id"] for r in rec_res.json()["data"]}

    # Apply manual overrides before session closes
    # 1. Override s_excused to EXCUSED
    exc_res = client.post(
        f"/api/v1/attendance/records/{records[s_excused]}/override",
        headers=headers,
        json={"status": "EXCUSED", "reason": "Medical certificate verified"},
    )
    assert exc_res.status_code == 200

    # 2. Override s_leave to LEAVE
    leave_res = client.post(
        f"/api/v1/attendance/records/{records[s_leave]}/override",
        headers=headers,
        json={"status": "LEAVE", "reason": "Official university sports team participation"},
    )
    assert leave_res.status_code == 200

    # 3. Close the session (evaluates records)
    close_res = client.post(f"/api/v1/attendance/sessions/{session_id}/close", headers=headers)
    assert close_res.status_code == 200

    # 4. Verify statuses are preserved and not overwritten to ABSENT
    final_records = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records", headers=headers
    ).json()["data"]
    final_by_sid = {r["student_id"]: r for r in final_records}

    assert final_by_sid[s_excused]["status"] == "EXCUSED"
    assert final_by_sid[s_leave]["status"] == "LEAVE"


def test_inv_01_client_cannot_mark_self_present(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify INV-01: Student client cannot mark itself present or call privileged credit
    endpoints.
    """
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    student_id = create_enrolled_student(client, admin_headers, offering_id, "inv01")

    # Create student user login credentials
    user_id, email, password = create_test_user(
        client, admin_headers, prefix=f"std_inv01_{uuid.uuid4().hex[:6]}"
    )
    # Get student auth headers
    student_headers = get_user_headers(client, email, password, str(test_university.id))

    # Initialize session as admin
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=admin_headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]

    # Student attempts to call manual-credit endpoint -> 403 Forbidden
    hack_res = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/manual-credit",
        headers=student_headers,
        json={"student_id": student_id, "reason": "Self-marking attempt"},
    )
    assert hack_res.status_code == 403

    # Unauthenticated attempt -> 401 Unauthorized
    unauth_res = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/manual-credit",
        json={"student_id": student_id, "reason": "Unauthenticated attempt"},
    )
    assert unauth_res.status_code == 401


def test_inv_05_no_duplicate_checkpoint_credit(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify INV-05: Student cannot receive multiple credits for the same checkpoint in a
    session.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)
    student_id = create_enrolled_student(client, headers, offering_id, "inv05")

    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]

    # 1. First credit for START checkpoint
    res1 = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/manual-credit",
        headers=headers,
        json={"student_id": student_id, "reason": "First credit"},
    )
    assert res1.status_code == 200
    assert res1.json()["data"]["verified"] is True

    # 2. Second credit for SAME START checkpoint -> Idempotent, verified is True
    res2 = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/manual-credit",
        headers=headers,
        json={"student_id": student_id, "reason": "Duplicate attempt"},
    )
    assert res2.status_code == 200
    assert res2.json()["data"]["verified"] is True

    # 3. Verify record shows exactly 1 checkpoint verified, not 2
    rec_res = client.get(f"/api/v1/attendance/sessions/{session_id}/records", headers=headers)
    r = next(rec for rec in rec_res.json()["data"] if rec["student_id"] == student_id)
    assert r["checkpoints_verified"] == 1
    assert r["start_credited"] is True
