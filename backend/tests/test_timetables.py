"""Test suite for recurring Timetable rules, schedule validation, and conflict detection."""

import uuid

from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_offerings import setup_academic_prerequisites
from backend.tests.test_people import create_test_user
from backend.tests.test_users import get_admin_headers


def create_test_room(client: TestClient, headers: dict[str, str], suffix: str) -> str:
    """Helper to create a building and room."""
    b_res = client.post(
        "/api/v1/buildings",
        headers=headers,
        json={"code": f"BLD_{suffix}".upper(), "name": "Academic Hall"},
    )
    assert b_res.status_code == 201
    b_id = b_res.json()["data"]["id"]

    r_res = client.post(
        "/api/v1/rooms",
        headers=headers,
        json={"building_id": b_id, "room_number": f"R-{suffix}", "capacity": 50},
    )
    assert r_res.status_code == 201
    return r_res.json()["data"]["id"]


def test_timetable_crud_and_boundary_validation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify timetable creation, time order validation, weekday limits, and semester boundaries."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers)
    suffix = uuid.uuid4().hex[:6]
    room_id = create_test_room(client, headers, suffix)

    # Create Offering
    off_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    assert off_res.status_code == 201
    offering_id = off_res.json()["data"]["id"]

    # 1. Invalid time: start_time >= end_time rejected
    inv_time_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": offering_id,
            "room_id": room_id,
            "weekday": 7,  # Sunday
            "start_time": "10:00:00",
            "end_time": "09:00:00",
        },
    )
    assert inv_time_res.status_code in (400, 422)

    # 2. Invalid weekday (< 1 or > 7) rejected
    inv_day_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": offering_id,
            "room_id": room_id,
            "weekday": 8,
            "start_time": "08:00:00",
            "end_time": "09:30:00",
        },
    )
    assert inv_day_res.status_code in (400, 422)

    # 3. Outside semester dates rejected (semester is 2026-09-01 to 2027-01-31)
    out_sem_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": offering_id,
            "room_id": room_id,
            "weekday": 7,
            "start_time": "08:00:00",
            "end_time": "09:30:00",
            "effective_from": "2026-08-01",  # Before semester starts
        },
    )
    assert out_sem_res.status_code in (400, 422)

    # 4. Valid Timetable Creation
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
            "effective_to": "2027-01-31",
        },
    )
    assert tt_res.status_code == 201
    tt_data = tt_res.json()["data"]
    tt_id = tt_data["id"]
    assert tt_data["weekday"] == 7
    assert tt_data["start_time"] == "08:00:00"
    assert tt_data["end_time"] == "09:30:00"
    assert tt_data["status"] == "ACTIVE"

    # 5. Multiple non-overlapping weekly meetings for same offering allowed (e.g. Tuesday 08:00)
    tt2_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": offering_id,
            "room_id": room_id,
            "weekday": 2,  # Tuesday
            "start_time": "08:00:00",
            "end_time": "09:30:00",
        },
    )
    assert tt2_res.status_code == 201

    # 6. Deactivate timetable
    deact_res = client.post(f"/api/v1/timetables/{tt_id}/deactivate", headers=headers)
    assert deact_res.status_code == 200
    assert deact_res.json()["data"]["status"] == "INACTIVE"


def test_room_conflict_detection_and_adjacent_slots(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify room conflict detection prevents overlapping bookings while
    allowing adjacent slots.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, ay_id = setup_academic_prerequisites(client, headers)
    suffix = uuid.uuid4().hex[:6]
    room_id = create_test_room(client, headers, suffix)

    # Offering 1
    off1_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    assert off1_res.status_code == 201
    off1_id = off1_res.json()["data"]["id"]

    # Offering 2 (Different Course & Section)
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

    # 1. Schedule Offering 1: Sunday 08:00–09:30 in room_id
    tt1_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": off1_id,
            "room_id": room_id,
            "weekday": 7,  # Sunday
            "start_time": "08:00:00",
            "end_time": "09:30:00",
        },
    )
    assert tt1_res.status_code == 201

    # 2. Overlapping Booking for Offering 2 in same room: Sunday 09:00–10:30 -> REJECTED 409
    conf_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": off2_id,
            "room_id": room_id,
            "weekday": 7,
            "start_time": "09:00:00",
            "end_time": "10:30:00",
        },
    )
    assert conf_res.status_code == 409
    assert conf_res.json()["error"]["code"] == "ROOM_SCHEDULE_CONFLICT"

    # 3. Adjacent Booking in same room: Sunday 09:30–11:00 -> ALLOWED (no conflict)
    adj_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": off2_id,
            "room_id": room_id,
            "weekday": 7,
            "start_time": "09:30:00",
            "end_time": "11:00:00",
        },
    )
    assert adj_res.status_code == 201

    # 4. Same room, same weekday, same time window,
    # but non-overlapping effective date ranges -> ALLOWED
    c3_res = client.post(
        "/api/v1/courses",
        headers=headers,
        json={"code": f"C3_{suffix}", "name": "Databases", "credit_hours": 3},
    )
    assert c3_res.status_code == 201
    c3_id = c3_res.json()["data"]["id"]
    off3_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={"course_id": c3_id, "semester_id": semester_id, "section_id": sec2_id},
    )
    assert off3_res.status_code == 201
    off3_id = off3_res.json()["data"]["id"]

    # Book room for Wednesday 08:00-09:30 for Sep 01 to Sep 30
    tt3_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": off3_id,
            "room_id": room_id,
            "weekday": 3,
            "start_time": "08:00:00",
            "end_time": "09:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-30",
        },
    )
    assert tt3_res.status_code == 201

    # Book SAME room for Wednesday 08:00-09:30 for Oct 01 to Oct 31
    # Non-overlapping effective dates -> ALLOWED (201)
    tt4_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": off2_id,
            "room_id": room_id,
            "weekday": 3,
            "start_time": "08:00:00",
            "end_time": "09:30:00",
            "effective_from": "2026-10-01",
            "effective_to": "2026-10-31",
        },
    )
    assert tt4_res.status_code == 201


def test_lecturer_and_section_conflict_detection(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify instructor and section cohort double-booking conflict detection."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers)
    suffix = uuid.uuid4().hex[:6]
    room1_id = create_test_room(client, headers, f"{suffix}_1")
    room2_id = create_test_room(client, headers, f"{suffix}_2")

    # Create Offering 1
    off1_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    assert off1_res.status_code == 201
    off1_id = off1_res.json()["data"]["id"]

    # Assign Lecturer to Offering 1
    u_id, _, _ = create_test_user(client, headers, prefix="prof")
    lec_res = client.post(
        "/api/v1/lecturers",
        headers=headers,
        json={"user_id": u_id, "employee_code": f"EMP_{suffix}"},
    )
    assert lec_res.status_code == 201
    lec_id = lec_res.json()["data"]["id"]

    assign1 = client.post(
        f"/api/v1/course-offerings/{off1_id}/lecturers",
        headers=headers,
        json={"lecturer_id": lec_id, "is_primary": True},
    )
    assert assign1.status_code == 201

    # Create Offering 2 with different course and section
    c2_res = client.post(
        "/api/v1/courses",
        headers=headers,
        json={"code": f"C2_{suffix}", "name": "Operating Systems", "credit_hours": 3},
    )
    assert c2_res.status_code == 201
    c2_id = c2_res.json()["data"]["id"]

    sec2_res = client.post(
        "/api/v1/sections",
        headers=headers,
        json={
            "code": f"S2_{suffix[:2].upper()}",
            "name": "Section Gamma",
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

    # Assign SAME Lecturer to Offering 2
    assign2 = client.post(
        f"/api/v1/course-offerings/{off2_id}/lecturers",
        headers=headers,
        json={"lecturer_id": lec_id, "is_primary": True},
    )
    assert assign2.status_code == 201

    # 1. Schedule Offering 1: Monday 08:00–09:30 in room 1 with lecturer
    tt1_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": off1_id,
            "room_id": room1_id,
            "lecturer_id": lec_id,
            "weekday": 1,  # Monday
            "start_time": "08:00:00",
            "end_time": "09:30:00",
        },
    )
    assert tt1_res.status_code == 201

    # 2. Schedule Offering 2 with SAME lecturer in DIFFERENT room (room2) at same time
    # -> LECTURER_SCHEDULE_CONFLICT
    lec_conf_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": off2_id,
            "room_id": room2_id,
            "lecturer_id": lec_id,
            "weekday": 1,  # Monday
            "start_time": "08:30:00",
            "end_time": "10:00:00",
        },
    )
    assert lec_conf_res.status_code == 409
    assert lec_conf_res.json()["error"]["code"] == "LECTURER_SCHEDULE_CONFLICT"

    # 3. Create Offering 3 for SAME Section (section_id)
    c3_res = client.post(
        "/api/v1/courses",
        headers=headers,
        json={"code": f"C3_{suffix}", "name": "Computer Networks", "credit_hours": 3},
    )
    assert c3_res.status_code == 201
    c3_id = c3_res.json()["data"]["id"]

    off3_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={"course_id": c3_id, "semester_id": semester_id, "section_id": section_id},
    )
    assert off3_res.status_code == 201
    off3_id = off3_res.json()["data"]["id"]

    # 4. Schedule Offering 3 for same Section at overlapping time in different room
    # -> SECTION_SCHEDULE_CONFLICT
    sec_conf_res = client.post(
        "/api/v1/timetables",
        headers=headers,
        json={
            "course_offering_id": off3_id,
            "room_id": room2_id,
            "weekday": 1,  # Monday
            "start_time": "08:30:00",
            "end_time": "10:00:00",
        },
    )
    assert sec_conf_res.status_code == 409
    assert sec_conf_res.json()["error"]["code"] == "SECTION_SCHEDULE_CONFLICT"
