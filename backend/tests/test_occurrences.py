"""Test suite for concrete ClassOccurrence generation, cancellation, and rescheduling."""

import uuid

from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_offerings import setup_academic_prerequisites
from backend.tests.test_timetables import create_test_room
from backend.tests.test_users import get_admin_headers


def test_occurrence_generation_and_idempotency(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify deterministic ClassOccurrence generation across semester calendar dates,

    UTC timestamp conversions, and generation idempotency (never duplicates).
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers)
    suffix = uuid.uuid4().hex[:6]
    room_id = create_test_room(client, headers, suffix)

    # 1. Create Offering
    off_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    assert off_res.status_code == 201
    offering_id = off_res.json()["data"]["id"]

    # 2. Create Timetable rule (Every Sunday 08:00–09:30, Semester: 2026-09-01 to 2027-01-31)
    tt_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": offering_id,
            "room_id": room_id,
            "weekday": 7,  # Sunday
            "start_time": "08:00:00",
            "end_time": "09:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-30",  # September only = 4 Sundays: Sep 6, 13, 20, 27
        },
    )
    assert tt_res.status_code == 201
    tt_id = tt_res.json()["data"]["id"]

    # 3. First generation run -> should generate exactly 4 occurrences
    gen1_res = client.post(
        f"/api/v1/timetables/{tt_id}/generate-occurrences",
        headers=headers,
    )
    assert gen1_res.status_code == 200
    gen1_data = gen1_res.json()["data"]
    assert gen1_data["generated_count"] == 4
    assert gen1_data["existing_count"] == 0

    # 4. Second generation run -> IDEMPOTENT: 0 generated, 4 existing
    gen2_res = client.post(
        f"/api/v1/timetables/{tt_id}/generate-occurrences",
        headers=headers,
    )
    assert gen2_res.status_code == 200
    gen2_data = gen2_res.json()["data"]
    assert gen2_data["generated_count"] == 0
    assert gen2_data["existing_count"] == 4

    # 5. Query generated occurrences
    occ_res = client.get(
        f"/api/v1/class-occurrences?course_offering_id={offering_id}",
        headers=headers,
    )
    assert occ_res.status_code == 200
    items = occ_res.json()["data"]["items"]
    assert len(items) == 4

    # Check dates and UTC conversion (Asia/Kabul is UTC+4:30)
    # 08:00 Kabul time = 03:30 UTC
    first_occ = items[0]
    assert first_occ["local_date"] == "2026-09-06"
    assert "03:30:00" in first_occ["scheduled_start_utc"]
    assert "05:00:00" in first_occ["scheduled_end_utc"]
    assert first_occ["status"] == "SCHEDULED"


def test_occurrence_cancellation_preserves_history(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify concrete class occurrence cancellation preserves history and updates reason."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers)
    suffix = uuid.uuid4().hex[:6]
    room_id = create_test_room(client, headers, suffix)

    off_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    offering_id = off_res.json()["data"]["id"]

    tt_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": offering_id,
            "room_id": room_id,
            "weekday": 1,  # Monday
            "start_time": "08:00:00",
            "end_time": "09:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-15",
        },
    )
    tt_id = tt_res.json()["data"]["id"]

    # Generate occurrences
    client.post(f"/api/v1/timetables/{tt_id}/generate-occurrences", headers=headers)

    occ_res = client.get(
        f"/api/v1/class-occurrences?course_offering_id={offering_id}",
        headers=headers,
    )
    items = occ_res.json()["data"]["items"]
    target_occ_id = items[0]["id"]

    # Cancel one occurrence
    cancel_res = client.post(
        f"/api/v1/class-occurrences/{target_occ_id}/cancel",
        headers=headers,
        json={"reason": "National holiday - campus closed"},
    )
    assert cancel_res.status_code == 200
    cancelled_data = cancel_res.json()["data"]
    assert cancelled_data["id"] == target_occ_id
    assert cancelled_data["status"] == "CANCELLED"
    assert cancelled_data["cancellation_reason"] == "National holiday - campus closed"

    # Verify occurrence still exists in database query with CANCELLED status
    check_res = client.get(f"/api/v1/class-occurrences/{target_occ_id}", headers=headers)
    assert check_res.status_code == 200
    assert check_res.json()["data"]["status"] == "CANCELLED"


def test_occurrence_rescheduling(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify rescheduling concrete class occurrence creates linked occurrence
    and preserves history.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers)
    suffix = uuid.uuid4().hex[:6]
    room_id = create_test_room(client, headers, suffix)

    off_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    offering_id = off_res.json()["data"]["id"]

    tt_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": offering_id,
            "room_id": room_id,
            "weekday": 7,  # Sunday
            "start_time": "08:00:00",
            "end_time": "09:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-10",
        },
    )
    tt_id = tt_res.json()["data"]["id"]

    client.post(f"/api/v1/timetables/{tt_id}/generate-occurrences", headers=headers)

    occ_res = client.get(
        f"/api/v1/class-occurrences?course_offering_id={offering_id}",
        headers=headers,
    )
    items = occ_res.json()["data"]["items"]
    target_occ_id = items[0]["id"]

    # Reschedule Sep 6 meeting to Tuesday Sep 8 at 10:00
    resched_res = client.post(
        f"/api/v1/class-occurrences/{target_occ_id}/reschedule",
        headers=headers,
        json={
            "new_date": "2026-09-08",
            "new_start_time": "10:00:00",
            "new_end_time": "11:30:00",
            "reason": "Makeup session for administrative delay",
        },
    )
    assert resched_res.status_code == 200
    new_occ_data = resched_res.json()["data"]
    assert new_occ_data["local_date"] == "2026-09-08"
    assert new_occ_data["status"] == "SCHEDULED"
    assert new_occ_data["rescheduled_from_id"] == target_occ_id

    # Check original is marked RESCHEDULED
    orig_res = client.get(f"/api/v1/class-occurrences/{target_occ_id}", headers=headers)
    assert orig_res.status_code == 200
    assert orig_res.json()["data"]["status"] == "RESCHEDULED"
    assert orig_res.json()["data"]["rescheduled_to_id"] == new_occ_data["id"]
