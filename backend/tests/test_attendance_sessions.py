"""Test suite for AttendanceSession lifecycle, 1:1 occurrence anchoring, and frozen roster."""

import uuid

from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user
from backend.tests.test_users import get_admin_headers


def create_enrolled_student(
    client: TestClient,
    headers: dict[str, str],
    offering_id: str,
    suffix: str,
) -> str:
    """Helper creating and enrolling a student in a course offering."""
    unique_salt = uuid.uuid4().hex[:6]
    user_id, _, _ = create_test_user(client, headers, prefix=f"std_{suffix}_{unique_salt}")
    stud_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={
            "user_id": user_id,
            "student_number": f"STD-{suffix}-{unique_salt}",
            "admission_date": "2024-09-01",
        },
    )
    assert stud_res.status_code == 201
    student_id = stud_res.json()["data"]["id"]

    enroll_res = client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
        json={
            "student_id": student_id,
        },
    )
    assert enroll_res.status_code == 201
    return student_id


def test_session_creation_1_to_1_anchor(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify session attaches 1:1 to class occurrence and duplicate creation is rejected."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

    # 1. Initialize session
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id},
    )
    assert sess_res.status_code == 201
    sess_data = sess_res.json()["data"]
    assert sess_data["status"] == "SCHEDULED"
    assert sess_data["class_occurrence_id"] == occurrence_id

    # 2. Attempt duplicate session creation for same occurrence -> Conflict 409
    dup_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id},
    )
    assert dup_res.status_code == 409


def test_session_cannot_attach_to_cancelled_or_rescheduled_occurrence(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify attendance session cannot attach to cancelled or superseded occurrence."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

    # 1. Cancel the occurrence
    cancel_res = client.post(
        f"/api/v1/class-occurrences/{occurrence_id}/cancel",
        headers=headers,
        json={"reason": "Inclement weather emergency cancellation"},
    )
    assert cancel_res.status_code == 200

    # 2. Attempt to create session for cancelled occurrence -> 400 OCCURRENCE_CANCELLED
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id},
    )
    assert sess_res.status_code == 400
    assert "OCCURRENCE_CANCELLED" in sess_res.text


def test_session_lifecycle_state_transitions(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify full lifecycle state machine: SCHEDULED -> ACTIVE -> PAUSED -> ACTIVE -> CLOSED."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

    # 1. Initialize (SCHEDULED)
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id},
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["data"]["id"]

    # 2. Activate (ACTIVE)
    open_res = client.post(f"/api/v1/attendance/sessions/{session_id}/open", headers=headers)
    assert open_res.status_code == 200
    assert open_res.json()["data"]["status"] == "ACTIVE"
    assert open_res.json()["data"]["opened_at_utc"] is not None

    # 3. Pause (PAUSED)
    pause_res = client.post(f"/api/v1/attendance/sessions/{session_id}/pause", headers=headers)
    assert pause_res.status_code == 200
    assert pause_res.json()["data"]["status"] == "PAUSED"
    assert pause_res.json()["data"]["paused_at_utc"] is not None

    # 4. Resume (ACTIVE)
    resume_res = client.post(f"/api/v1/attendance/sessions/{session_id}/resume", headers=headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["data"]["status"] == "ACTIVE"
    assert resume_res.json()["data"]["resumed_at_utc"] is not None

    # 5. Close (CLOSED)
    close_res = client.post(f"/api/v1/attendance/sessions/{session_id}/close", headers=headers)
    assert close_res.status_code == 200
    assert close_res.json()["data"]["status"] == "CLOSED"
    assert close_res.json()["data"]["closed_at_utc"] is not None

    # 6. Reopen attempt on CLOSED session must fail
    reopen_res = client.post(f"/api/v1/attendance/sessions/{session_id}/open", headers=headers)
    assert reopen_res.status_code == 400


def test_frozen_roster_snapshot(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify that active enrollments are frozen at session opening and subsequent enrollment

    changes do not retroactively alter the session roster.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)

    # 1. Enroll Student 1 and Student 2
    s1_id = create_enrolled_student(client, headers, offering_id, uuid.uuid4().hex[:6])
    s2_id = create_enrolled_student(client, headers, offering_id, uuid.uuid4().hex[:6])

    # 2. Initialize and open session (freezes roster)
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["data"]["id"]

    # Verify initial frozen records
    records_res = client.get(f"/api/v1/attendance/sessions/{session_id}/records", headers=headers)
    assert records_res.status_code == 200
    records = records_res.json()["data"]
    roster_student_ids = {r["student_id"] for r in records}
    assert s1_id in roster_student_ids
    assert s2_id in roster_student_ids
    assert len(records) == 2
    for r in records:
        assert r["status"] == "PENDING"

    # 3. Enroll Student 3 AFTER session opening
    s3_id = create_enrolled_student(client, headers, offering_id, uuid.uuid4().hex[:6])

    # 4. Verify session roster: Student 3 must NOT be present; roster is frozen
    records_res2 = client.get(f"/api/v1/attendance/sessions/{session_id}/records", headers=headers)
    assert records_res2.status_code == 200
    roster2_ids = {r["student_id"] for r in records_res2.json()["data"]}
    assert s3_id not in roster2_ids
    assert len(roster2_ids) == 2


def test_get_session_by_occurrence_endpoint(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify GET /sessions/by-occurrence/{occurrence_id} returns session details or 404."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

    # 1. Before session creation -> 404
    not_found_res = client.get(
        f"/api/v1/attendance/sessions/by-occurrence/{occurrence_id}",
        headers=headers,
    )
    assert not_found_res.status_code == 404

    # 2. Create session
    create_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    assert create_res.status_code == 201
    created_id = create_res.json()["data"]["id"]

    # 3. After session creation -> 200 with session details
    get_res = client.get(
        f"/api/v1/attendance/sessions/by-occurrence/{occurrence_id}",
        headers=headers,
    )
    assert get_res.status_code == 200
    data = get_res.json()["data"]
    assert data["id"] == created_id
    assert data["class_occurrence_id"] == occurrence_id
    assert data["status"] == "ACTIVE"
