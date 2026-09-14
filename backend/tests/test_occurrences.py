"""Test suite for concrete ClassOccurrence generation, cancellation, and rescheduling."""

import uuid

from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_offerings import setup_academic_prerequisites
from backend.tests.test_people import create_test_user
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


def test_rescheduling_conflicts_and_timetable_immutability(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify rescheduling checks ROOM, LECTURER, and SECTION conflicts,

    and verify timetable updates never rewrite past occurrences.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers)
    suffix = uuid.uuid4().hex[:6]
    room1_id = create_test_room(client, headers, f"{suffix}_1")
    room2_id = create_test_room(client, headers, f"{suffix}_2")

    # 1. Create Lecturer
    u_id, _, _ = create_test_user(client, headers, prefix="prof")
    lec_res = client.post(
        "/api/v1/lecturers",
        headers=headers,
        json={"user_id": u_id, "employee_code": f"EMP_{suffix}"},
    )
    assert lec_res.status_code == 201
    lec_id = lec_res.json()["data"]["id"]

    # 2. Offering 1 (with lecturer and section 1)
    off1_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    assert off1_res.status_code == 201
    off1_id = off1_res.json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{off1_id}/lecturers",
        headers=headers,
        json={"lecturer_id": lec_id, "is_primary": True},
    )

    # 3. Offering 2 (Different Course & Section, also assigned to same lecturer)
    c2_res = client.post(
        "/api/v1/courses",
        headers=headers,
        json={"code": f"C2_{suffix}", "name": "Algorithms", "credit_hours": 3},
    )
    assert c2_res.status_code == 201
    c2_id = c2_res.json()["data"]["id"]
    sec2_res = client.post(
        "/api/v1/sections",
        headers=headers,
        json={
            "code": f"S2_{suffix[:2].upper()}",
            "name": "Section Beta",
            "semester_id": semester_id,
        },
    )
    assert sec2_res.status_code == 201
    sec2_id = sec2_res.json()["data"]["id"]

    off2_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={"course_id": c2_id, "semester_id": semester_id, "section_id": sec2_id},
    )
    assert off2_res.status_code == 201
    off2_id = off2_res.json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{off2_id}/lecturers",
        headers=headers,
        json={"lecturer_id": lec_id, "is_primary": True},
    )

    # 4. Generate occurrences for Offering 1
    # (Sunday 08:00-09:30, Room 1, Sep 1 to Sep 30 = 4 Sundays)
    tt1_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": off1_id,
            "room_id": room1_id,
            "lecturer_id": lec_id,
            "weekday": 7,  # Sunday
            "start_time": "08:00:00",
            "end_time": "09:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-30",
        },
    )
    assert tt1_res.status_code == 201
    tt1_id = tt1_res.json()["data"]["id"]
    client.post(f"/api/v1/timetables/{tt1_id}/generate-occurrences", headers=headers)

    # 5. Generate occurrences for Offering 2
    # (Sunday 10:00-11:30 in Room 2, Sep 1 to Sep 30 = 4 Sundays)
    tt2_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": off2_id,
            "room_id": room2_id,
            "lecturer_id": lec_id,
            "weekday": 7,  # Sunday
            "start_time": "10:00:00",
            "end_time": "11:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-30",
        },
    )
    assert tt2_res.status_code == 201
    tt2_id = tt2_res.json()["data"]["id"]
    client.post(f"/api/v1/timetables/{tt2_id}/generate-occurrences", headers=headers)

    # 6. Verify multiple weekly rules generate occurrences correctly
    # Add a Tuesday rule for Offering 2 and generate occurrences
    tt2_tue_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": off2_id,
            "room_id": room2_id,
            "weekday": 2,  # Tuesday
            "start_time": "10:00:00",
            "end_time": "11:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-30",
        },
    )
    assert tt2_tue_res.status_code == 201
    tt2_tue_id = tt2_tue_res.json()["data"]["id"]
    gen_tue = client.post(f"/api/v1/timetables/{tt2_tue_id}/generate-occurrences", headers=headers)
    assert gen_tue.status_code == 200
    # 5 Tuesdays in Sep 2026: 1, 8, 15, 22, 29
    assert gen_tue.json()["data"]["generated_count"] == 5

    # Total occurrences for Offering 2 should now be 4 (Sunday) + 5 (Tuesday) = 9
    occ2_res = client.get(
        f"/api/v1/class-occurrences?course_offering_id={off2_id}",
        headers=headers,
    )
    assert occ2_res.status_code == 200
    assert len(occ2_res.json()["data"]["items"]) == 9

    # 7. Verify timetable changes NEVER rewrite past occurrences
    # Update Timetable 1 start time from 08:00 to 08:30
    patch_tt = client.patch(
        f"/api/v1/timetables/{tt1_id}",
        headers=headers,
        json={"start_time": "08:30:00"},
    )
    assert patch_tt.status_code == 200
    # Query occurrences: Sep 6 meeting still exists with original 08:00 start
    occ1_res = client.get(
        f"/api/v1/class-occurrences?course_offering_id={off1_id}",
        headers=headers,
    )
    assert occ1_res.status_code == 200
    occ1_items = occ1_res.json()["data"]["items"]
    assert len(occ1_items) == 4
    first_occ = next(o for o in occ1_items if o["local_date"] == "2026-09-06")
    assert "03:30:00" in first_occ["scheduled_start_utc"]  # 08:00 Kabul = 03:30 UTC, untouched!

    # 8. Test rescheduling checks ROOM conflict
    # Try to reschedule Sep 6 occurrence of Offering 1 to Room 2 on Sep 6 at 10:00-11:30
    # Room 2 is already booked for Offering 2 at that exact time -> 409 ROOM_SCHEDULE_CONFLICT
    resched_room_conf = client.post(
        f"/api/v1/class-occurrences/{first_occ['id']}/reschedule",
        headers=headers,
        json={
            "new_date": "2026-09-06",
            "new_start_time": "10:00:00",
            "new_end_time": "11:30:00",
            "new_room_id": room2_id,
            "reason": "Test room conflict check",
        },
    )
    assert resched_room_conf.status_code == 409
    assert resched_room_conf.json()["error"]["code"] == "ROOM_SCHEDULE_CONFLICT"

    # 9. Test rescheduling checks LECTURER conflict
    # Reschedule Sep 6 occurrence to Room 1 (no room conflict) at 10:00-11:30
    # But Lecturer is already teaching Offering 2 at 10:00-11:30 -> 409 LECTURER_SCHEDULE_CONFLICT
    resched_lec_conf = client.post(
        f"/api/v1/class-occurrences/{first_occ['id']}/reschedule",
        headers=headers,
        json={
            "new_date": "2026-09-06",
            "new_start_time": "10:00:00",
            "new_end_time": "11:30:00",
            "new_room_id": room1_id,
            "reason": "Test lecturer conflict check",
        },
    )
    assert resched_lec_conf.status_code == 409
    assert resched_lec_conf.json()["error"]["code"] == "LECTURER_SCHEDULE_CONFLICT"

    # 10. Test rescheduling checks SECTION conflict
    # Create Offering 3 with SAME Section (section_id)
    c3_res = client.post(
        "/api/v1/courses",
        headers=headers,
        json={"code": f"C3_{suffix}", "name": "Networks", "credit_hours": 3},
    )
    c3_id = c3_res.json()["data"]["id"]
    off3_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={"course_id": c3_id, "semester_id": semester_id, "section_id": section_id},
    )
    assert off3_res.status_code == 201
    off3_id = off3_res.json()["data"]["id"]

    # Generate occurrence for Offering 3 on Wednesday 14:00-15:30 in Room 2
    # (different room, different lecturer)
    tt3_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": off3_id,
            "room_id": room2_id,
            "weekday": 3,  # Wednesday
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-30",
        },
    )
    assert tt3_res.status_code == 201
    tt3_id = tt3_res.json()["data"]["id"]
    client.post(f"/api/v1/timetables/{tt3_id}/generate-occurrences", headers=headers)

    # Now attempt to reschedule Offering 1 occurrence to Wednesday Sep 9 at 14:00-15:30 in Room 1
    # with a substitute lecturer (so neither room nor lecturer conflicts, but section 1 has a class)
    # -> 409 SECTION_SCHEDULE_CONFLICT
    u_sub_id, _, _ = create_test_user(client, headers, prefix="sub")
    sub_lec_res = client.post(
        "/api/v1/lecturers",
        headers=headers,
        json={"user_id": u_sub_id, "employee_code": f"SUB_{suffix}"},
    )
    assert sub_lec_res.status_code == 201
    sub_lec_id = sub_lec_res.json()["data"]["id"]

    resched_sec_conf = client.post(
        f"/api/v1/class-occurrences/{first_occ['id']}/reschedule",
        headers=headers,
        json={
            "new_date": "2026-09-09",
            "new_start_time": "14:00:00",
            "new_end_time": "15:30:00",
            "new_room_id": room1_id,
            "substitute_lecturer_id": sub_lec_id,
            "reason": "Test section conflict check",
        },
    )
    assert resched_sec_conf.status_code == 409
    assert resched_sec_conf.json()["error"]["code"] == "SECTION_SCHEDULE_CONFLICT"
