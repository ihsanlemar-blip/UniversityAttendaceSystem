"""Integration tests for Timetable Schedule Data Import and Safe Commit."""

import datetime
import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import (
    ImportJobStatus,
    ImportRowAction,
    ImportRowStatus,
)
from backend.app.models.timetable import Timetable
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_people import create_test_user
from backend.tests.test_users import get_admin_headers


def setup_timetable_prerequisites(client: TestClient, headers: dict[str, str]) -> dict[str, str]:
    """Helper to set up course, semester, section, offering, building, room, and lecturer."""
    suffix = uuid.uuid4().hex[:6].upper()
    course_code = f"CS-TT-{suffix}"
    sem_code = f"SEM-TT-{suffix}"
    sec_code = f"SEC-TT-{suffix}"
    bld_code = f"BLD-TT-{suffix}"
    room_num = f"R-{suffix}"
    emp_code = f"LEC-TT-{suffix}"

    # 1. Course
    c_res = client.post(
        "/api/v1/courses",
        headers=headers,
        json={"code": course_code, "name": "Networks", "credit_hours": 3},
    )
    assert c_res.status_code == 201
    course_id = c_res.json()["data"]["id"]

    # 2. Academic Year
    ay_res = client.post(
        "/api/v1/academic-years",
        headers=headers,
        json={
            "name": f"AY {suffix}",
            "code": f"AY_{suffix}",
            "start_date": "2026-09-01",
            "end_date": "2027-06-30",
        },
    )
    assert ay_res.status_code == 201
    ay_id = ay_res.json()["data"]["id"]

    # 3. Semester
    sem_res = client.post(
        "/api/v1/semesters",
        headers=headers,
        json={
            "academic_year_id": ay_id,
            "name": f"Semester {suffix}",
            "code": sem_code,
            "sequence_order": 1,
            "start_date": "2026-09-01",
            "end_date": "2027-01-31",
        },
    )
    assert sem_res.status_code == 201
    semester_id = sem_res.json()["data"]["id"]

    # 4. Section
    sec_res = client.post(
        "/api/v1/sections",
        headers=headers,
        json={"code": sec_code, "name": f"Section {suffix}", "semester_id": semester_id},
    )
    assert sec_res.status_code == 201
    section_id = sec_res.json()["data"]["id"]

    # 5. Course Offering
    off_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    assert off_res.status_code == 201
    offering_id = off_res.json()["data"]["id"]

    # 6. Building & Room
    b_res = client.post(
        "/api/v1/buildings",
        headers=headers,
        json={"code": bld_code, "name": f"Science Hall {suffix}"},
    )
    assert b_res.status_code == 201
    building_id = b_res.json()["data"]["id"]

    r_res = client.post(
        "/api/v1/rooms",
        headers=headers,
        json={"building_id": building_id, "room_number": room_num, "capacity": 60},
    )
    assert r_res.status_code == 201
    room_id = r_res.json()["data"]["id"]

    # 7. Lecturer
    u_id, _, _ = create_test_user(client, headers, prefix=f"lec_{suffix.lower()}")
    l_res = client.post(
        "/api/v1/lecturers",
        headers=headers,
        json={"user_id": u_id, "employee_code": emp_code, "title": "Assistant Professor"},
    )
    assert l_res.status_code == 201
    lecturer_id = l_res.json()["data"]["id"]

    return {
        "course_code": course_code,
        "semester_code": sem_code,
        "section_code": sec_code,
        "building_code": bld_code,
        "room_number": room_num,
        "lecturer_code": emp_code,
        "offering_id": offering_id,
        "room_id": room_id,
        "lecturer_id": lecturer_id,
    }


@pytest.mark.asyncio
async def test_timetable_import_preview_non_mutation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """INVARIANT: Preview MUST NEVER mutate production timetables table."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    p = setup_timetable_prerequisites(client, headers)

    csv_content = (
        "course_code,semester_code,section_code,weekday,start_time,end_time,building_code,room_number,lecturer_code\n"
        f"{p['course_code']},{p['semester_code']},{p['section_code']},1,08:30,10:00,{p['building_code']},{p['room_number']},{p['lecturer_code']}\n"
    ).encode()

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "TIMETABLES", "commit_mode": "STRICT"},
        files={"file": ("timetable_preview.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201, res.text
    body = res.json()["data"]
    job_id = body["job"]["id"]

    assert body["job"]["row_count"] == 1
    assert body["job"]["valid_count"] == 1
    assert body["job"]["error_count"] == 0
    assert body["job"]["status"] == ImportJobStatus.READY.value

    # Verify staging rows
    rows_res = client.get(f"/api/v1/imports/{job_id}/rows", headers=headers)
    assert rows_res.status_code == 200
    rows_data = rows_res.json()["data"]["items"]
    assert len(rows_data) == 1
    assert rows_data[0]["status"] == ImportRowStatus.VALID.value
    assert rows_data[0]["action"] == ImportRowAction.CREATE.value

    # CRITICAL INVARIANT: Production table must NOT contain this timetable
    tt_stmt = select(Timetable).where(
        Timetable.university_id == test_university.id,
        Timetable.course_offering_id == uuid.UUID(p["offering_id"]),
    )
    assert (await db_session.execute(tt_stmt)).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_timetable_import_commit_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify committing staged timetables creates Timetable record."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    p = setup_timetable_prerequisites(client, headers)

    csv_content = (
        "course_code,semester_code,section_code,weekday,start_time,end_time,building_code,room_number,lecturer_code\n"
        f"{p['course_code']},{p['semester_code']},{p['section_code']},2,10:30,12:00,{p['building_code']},{p['room_number']},{p['lecturer_code']}\n"
    ).encode()

    # 1. Preview
    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "TIMETABLES", "commit_mode": "STRICT"},
        files={"file": ("timetable.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201
    job_id = res.json()["data"]["job"]["id"]

    # 2. Commit
    commit_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=headers, json={})
    assert commit_res.status_code == 200, commit_res.text
    commit_data = commit_res.json()["data"]
    assert commit_data["status"] == ImportJobStatus.COMPLETED.value
    assert commit_data["commit_count"] == 1

    # 3. Verify in database
    tt_stmt = select(Timetable).where(
        Timetable.university_id == test_university.id,
        Timetable.course_offering_id == uuid.UUID(p["offering_id"]),
    )
    tt = (await db_session.execute(tt_stmt)).scalar_one_or_none()
    assert tt is not None
    assert tt.weekday == 2
    assert tt.start_time == datetime.time(10, 30)
    assert tt.end_time == datetime.time(12, 0)
    assert tt.room_id == uuid.UUID(p["room_id"])
    assert tt.lecturer_id == uuid.UUID(p["lecturer_id"])

    # Double commit rejected
    double_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=headers, json={})
    assert double_res.status_code == 409


@pytest.mark.asyncio
async def test_timetable_import_intra_file_room_conflict(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify intra-file room schedule overlapping times trigger conflict error."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    p = setup_timetable_prerequisites(client, headers)

    # Two rows: both assign the same room on Monday at overlapping times
    # (08:30-10:00 and 09:30-11:00)
    csv_content = (
        "course_code,semester_code,section_code,weekday,start_time,end_time,building_code,room_number\n"
        f"{p['course_code']},{p['semester_code']},{p['section_code']},1,08:30,10:00,{p['building_code']},{p['room_number']}\n"
        f"{p['course_code']},{p['semester_code']},{p['section_code']},1,09:30,11:00,{p['building_code']},{p['room_number']}\n"
    ).encode()

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "TIMETABLES", "commit_mode": "STRICT"},
        files={"file": ("conflict_tt.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201
    job = res.json()["data"]["job"]
    assert job["error_count"] == 1

    job_id = job["id"]
    rows_res = client.get(f"/api/v1/imports/{job_id}/rows", headers=headers)
    rows = rows_res.json()["data"]["items"]

    # Row 0 valid
    assert rows[0]["status"] == ImportRowStatus.VALID.value

    # Row 1 conflict error
    assert rows[1]["status"] == ImportRowStatus.ERROR.value
    err_codes = [e["code"] for e in rows[1]["errors"]]
    assert "ROOM_SCHEDULE_CONFLICT_IN_FILE" in err_codes


@pytest.mark.asyncio
async def test_timetable_import_invalid_times_and_weekday(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify invalid weekday and start_time >= end_time trigger row validation errors."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    p = setup_timetable_prerequisites(client, headers)

    csv_content = (
        "course_code,semester_code,section_code,weekday,start_time,end_time\n"
        f"{p['course_code']},{p['semester_code']},{p['section_code']},8,08:30,10:00\n"
        f"{p['course_code']},{p['semester_code']},{p['section_code']},3,11:00,09:00\n"
    ).encode()

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "TIMETABLES", "commit_mode": "STRICT"},
        files={"file": ("invalid_tt.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201
    job = res.json()["data"]["job"]
    assert job["error_count"] == 2

    job_id = job["id"]
    rows_res = client.get(f"/api/v1/imports/{job_id}/rows", headers=headers)
    rows = rows_res.json()["data"]["items"]

    r0_codes = [e["code"] for e in rows[0]["errors"]]
    assert "INVALID_WEEKDAY" in r0_codes

    r1_codes = [e["code"] for e in rows[1]["errors"]]
    assert "INVALID_TIME_RANGE" in r1_codes
