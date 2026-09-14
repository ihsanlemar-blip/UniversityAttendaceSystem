"""Test suite for Attendance Policy creation, validation, hierarchy resolution, and immutability."""

import uuid

from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_offerings import setup_academic_prerequisites
from backend.tests.test_timetables import create_test_room
from backend.tests.test_users import get_admin_headers


def setup_class_occurrence(client: TestClient, headers: dict[str, str]) -> tuple[str, str, str]:
    """Helper creating course, offering, room, timetable, and occurrence."""
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers)
    suffix = uuid.uuid4().hex[:6]
    room_id = create_test_room(client, headers, suffix)

    off_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    assert off_res.status_code == 201
    offering_id = off_res.json()["data"]["id"]

    tt_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": offering_id,
            "room_id": room_id,
            "weekday": 1,
            "start_time": "08:00:00",
            "end_time": "09:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-15",
        },
    )
    assert tt_res.status_code == 201
    tt_id = tt_res.json()["data"]["id"]

    gen_res = client.post(f"/api/v1/timetables/{tt_id}/generate-occurrences", headers=headers)
    assert gen_res.status_code == 200
    assert gen_res.json()["data"]["generated_count"] > 0

    occ_res = client.get(
        f"/api/v1/class-occurrences?course_offering_id={offering_id}",
        headers=headers,
    )
    assert occ_res.status_code == 200
    items = occ_res.json()["data"]["items"]
    assert len(items) > 0
    occurrence_id = items[0]["id"]
    return course_id, offering_id, occurrence_id


def test_attendance_policy_creation_and_defaults(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify attendance policy creation with default institutional values."""
    headers = get_admin_headers(client, test_admin_user, test_university)

    res = client.post(
        "/api/v1/attendance/policies",
        headers=headers,
        json={
            "name": f"University Default Policy {uuid.uuid4().hex[:6]}",
            "scope_type": "UNIVERSITY",
        },
    )
    assert res.status_code == 201
    data = res.json()["data"]

    # Verify approved baseline defaults
    assert data["min_attendance_percentage"] == 75.0
    assert data["late_threshold_minutes"] == 10
    assert data["lecturer_correction_window_hours"] == 24
    assert data["required_checkpoint_count"] == 3
    assert data["checkpoint_duration_seconds"] == 300
    assert data["token_rotation_seconds"] == 30
    assert data["scope_type"] == "UNIVERSITY"
    assert "111" in data["status_mapping"]
    assert data["status_mapping"]["111"] == "PRESENT"
    assert data["status_mapping"]["000"] == "ABSENT"


def test_attendance_policy_validation_constraints(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify validation boundaries: percentages 0-100, durations 60-3600s."""
    headers = get_admin_headers(client, test_admin_user, test_university)

    # Invalid minimum percentage > 100
    bad_pct = client.post(
        "/api/v1/attendance/policies",
        headers=headers,
        json={"name": "Bad Pct", "min_attendance_percentage": 105.0},
    )
    assert bad_pct.status_code == 422

    # Invalid duration < 60s
    bad_dur = client.post(
        "/api/v1/attendance/policies",
        headers=headers,
        json={"name": "Bad Duration", "checkpoint_duration_seconds": 30},
    )
    assert bad_dur.status_code == 422

    # Invalid required checkpoint count > 3
    bad_cp = client.post(
        "/api/v1/attendance/policies",
        headers=headers,
        json={"name": "Bad Checkpoints", "required_checkpoint_count": 4},
    )
    assert bad_cp.status_code == 422


def test_attendance_policy_hierarchy_resolution(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify hierarchical policy precedence: Course override > University default."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, _, occurrence_id = setup_class_occurrence(client, headers)

    # 1. Create University Default Policy (75% min)
    uni_res = client.post(
        "/api/v1/attendance/policies",
        headers=headers,
        json={
            "name": f"Institutional Policy {uuid.uuid4().hex[:6]}",
            "scope_type": "UNIVERSITY",
            "min_attendance_percentage": 75.0,
            "checkpoint_duration_seconds": 300,
        },
    )
    assert uni_res.status_code == 201

    # 2. Create Course Policy Override (85% min, 180s duration)
    course_res = client.post(
        "/api/v1/attendance/policies",
        headers=headers,
        json={
            "name": f"Course Specific Policy {uuid.uuid4().hex[:6]}",
            "scope_type": "COURSE",
            "course_id": course_id,
            "min_attendance_percentage": 85.0,
            "checkpoint_duration_seconds": 180,
        },
    )
    assert course_res.status_code == 201
    course_policy_id = course_res.json()["data"]["id"]

    # 3. Initialize attendance session without explicit policy -> should resolve course override
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id},
    )
    assert sess_res.status_code == 201
    sess_data = sess_res.json()["data"]

    # Must resolve course policy override
    assert sess_data["attendance_policy_id"] == course_policy_id
    assert sess_data["policy_snapshot"]["min_attendance_percentage"] == 85.0
    assert sess_data["policy_snapshot"]["checkpoint_duration_seconds"] == 180


def test_attendance_policy_snapshot_immutability(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify that updating a policy does NOT mutate existing session snapshots."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

    # 1. Create Policy
    pol_res = client.post(
        "/api/v1/attendance/policies",
        headers=headers,
        json={
            "name": f"Snapshot Policy {uuid.uuid4().hex[:6]}",
            "scope_type": "UNIVERSITY",
            "min_attendance_percentage": 70.0,
            "checkpoint_duration_seconds": 240,
        },
    )
    assert pol_res.status_code == 201
    policy_id = pol_res.json()["data"]["id"]

    # 2. Initialize session with this policy
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={
            "class_occurrence_id": occurrence_id,
            "attendance_policy_id": policy_id,
        },
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["data"]["id"]
    snapshot_before = sess_res.json()["data"]["policy_snapshot"]
    assert snapshot_before["min_attendance_percentage"] == 70.0
    assert snapshot_before["checkpoint_duration_seconds"] == 240

    # 3. Update Policy to 90% and 120s
    patch_res = client.patch(
        f"/api/v1/attendance/policies/{policy_id}",
        headers=headers,
        json={
            "min_attendance_percentage": 90.0,
            "checkpoint_duration_seconds": 120,
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["min_attendance_percentage"] == 90.0

    # 4. Re-fetch session -> Snapshot MUST remain intact at 70% and 240s
    get_sess_res = client.get(f"/api/v1/attendance/sessions/{session_id}", headers=headers)
    assert get_sess_res.status_code == 200
    snapshot_after = get_sess_res.json()["data"]["policy_snapshot"]
    assert snapshot_after["min_attendance_percentage"] == 70.0
    assert snapshot_after["checkpoint_duration_seconds"] == 240
