"""Test suite for Attendance RBAC, lecturer occurrence scoping, department isolation,
and student privacy.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import ScopeType, SystemRole
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_offerings import setup_academic_prerequisites
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_timetables import create_test_room
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_lecturer_assigned_occurrence_access_and_unassigned_denial(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify assigned lecturer has attendance authority while unassigned lecturer receives 403."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, admin_headers)
    suffix = uuid.uuid4().hex[:6]
    room_id = create_test_room(client, admin_headers, suffix)

    # 1. Create Course Offering 1 & 2
    off1_res = client.post(
        "/api/v1/course-offerings",
        headers=admin_headers,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    off1_id = off1_res.json()["data"]["id"]

    c2_res = client.post(
        "/api/v1/courses",
        headers=admin_headers,
        json={"code": f"C2_{suffix}", "name": "Advanced Physics", "credit_hours": 3},
    )
    c2_id = c2_res.json()["data"]["id"]
    off2_res = client.post(
        "/api/v1/course-offerings",
        headers=admin_headers,
        json={"course_id": c2_id, "semester_id": semester_id, "section_id": section_id},
    )
    off2_id = off2_res.json()["data"]["id"]

    # 2. Create Lecturer A (teaches Offering 1)
    lec_a_user_id, lec_a_name, lec_a_pwd = create_test_user(client, admin_headers, prefix="lec_a")
    lec_a_res = client.post(
        "/api/v1/lecturers",
        headers=admin_headers,
        json={"user_id": lec_a_user_id, "employee_code": f"LECA_{suffix}"},
    )
    lec_a_id = lec_a_res.json()["data"]["id"]

    # Assign Lecturer A to Offering 1
    client.post(
        f"/api/v1/course-offerings/{off1_id}/lecturers",
        headers=admin_headers,
        json={"lecturer_id": lec_a_id, "is_primary": True},
    )

    # 3. Create Lecturer B (teaches Offering 2)
    lec_b_user_id, lec_b_name, lec_b_pwd = create_test_user(client, admin_headers, prefix="lec_b")
    lec_b_res = client.post(
        "/api/v1/lecturers",
        headers=admin_headers,
        json={"user_id": lec_b_user_id, "employee_code": f"LECB_{suffix}"},
    )
    lec_b_id = lec_b_res.json()["data"]["id"]

    client.post(
        f"/api/v1/course-offerings/{off2_id}/lecturers",
        headers=admin_headers,
        json={"lecturer_id": lec_b_id, "is_primary": True},
    )

    # 4. Assign SystemRole.LECTURER to both users
    role_res = await db_session.execute(
        Role.__table__.select().where(Role.code == SystemRole.LECTURER.value)
    )
    lec_role = role_res.first()
    assert lec_role is not None

    db_session.add(
        RoleAssignment(
            user_id=uuid.UUID(lec_a_user_id),
            role_id=lec_role.id,
            university_id=test_university.id,
            scope_type=ScopeType.UNIVERSITY.value,
            scope_id=test_university.id,
        )
    )
    db_session.add(
        RoleAssignment(
            user_id=uuid.UUID(lec_b_user_id),
            role_id=lec_role.id,
            university_id=test_university.id,
            scope_type=ScopeType.UNIVERSITY.value,
            scope_id=test_university.id,
        )
    )
    await db_session.commit()

    # 5. Generate occurrences for Offering 1 and Offering 2
    tt1_res = client.post(
        "/api/v1/timetables",
        headers=admin_headers,
        json={
            "course_offering_id": off1_id,
            "room_id": room_id,
            "weekday": 7,
            "start_time": "08:00:00",
            "end_time": "09:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-10",
        },
    )
    tt1_id = tt1_res.json()["data"]["id"]
    client.post(f"/api/v1/timetables/{tt1_id}/generate-occurrences", headers=admin_headers)

    tt2_res = client.post(
        "/api/v1/timetables",
        headers=admin_headers,
        json={
            "course_offering_id": off2_id,
            "room_id": room_id,
            "weekday": 1,
            "start_time": "10:00:00",
            "end_time": "11:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-10",
        },
    )
    tt2_id = tt2_res.json()["data"]["id"]
    client.post(f"/api/v1/timetables/{tt2_id}/generate-occurrences", headers=admin_headers)

    # Fetch occurrences
    occs1 = client.get(
        f"/api/v1/class-occurrences?course_offering_id={off1_id}", headers=admin_headers
    ).json()["data"]["items"]
    assert len(occs1) > 0
    occ1_id = occs1[0]["id"]

    occs2 = client.get(
        f"/api/v1/class-occurrences?course_offering_id={off2_id}", headers=admin_headers
    ).json()["data"]["items"]
    assert len(occs2) > 0
    occ2_id = occs2[0]["id"]

    # 6. Lecturer A logs in
    lec_a_headers = get_user_headers(client, lec_a_name, lec_a_pwd, str(test_university.id))

    # Lecturer A CAN initialize session for Offering 1
    sess1_res = client.post(
        "/api/v1/attendance/sessions",
        headers=lec_a_headers,
        json={"class_occurrence_id": occ1_id, "activate_immediately": True},
    )
    assert sess1_res.status_code == 201
    sess1_id = sess1_res.json()["data"]["id"]

    # Lecturer A CAN open checkpoint for Offering 1
    open_res = client.post(
        f"/api/v1/attendance/sessions/{sess1_id}/checkpoints/START/open",
        headers=lec_a_headers,
        json={"window_duration_seconds": 180},
    )
    assert open_res.status_code == 200

    # 7. Lecturer A CANNOT initialize session for Offering 2 (not assigned -> 403)
    sess2_res = client.post(
        "/api/v1/attendance/sessions",
        headers=lec_a_headers,
        json={"class_occurrence_id": occ2_id, "activate_immediately": True},
    )
    assert sess2_res.status_code == 403
    assert "PERMISSION_DENIED" in sess2_res.text


@pytest.mark.asyncio
async def test_department_admin_academic_unit_scoping(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify Department Admin has authority in own department and is denied sibling departments."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Create Dept A and Dept B (siblings under same university)
    da_res = client.post(
        "/api/v1/academic-units",
        headers=admin_headers,
        json={"name": "Dept CS", "code": f"CS_{suffix}", "unit_type": "DEPARTMENT"},
    )
    da_id = da_res.json()["data"]["id"]

    db_res = client.post(
        "/api/v1/academic-units",
        headers=admin_headers,
        json={"name": "Dept Math", "code": f"MTH_{suffix}", "unit_type": "DEPARTMENT"},
    )
    db_id = db_res.json()["data"]["id"]

    # Create Department Admin user scoped to Dept A
    da_user_id, da_name, da_pwd = create_test_user(client, admin_headers, prefix="da_user")
    role_res = await db_session.execute(
        Role.__table__.select().where(Role.code == SystemRole.DEPARTMENT_ADMIN.value)
    )
    da_role = role_res.first()
    assert da_role is not None

    db_session.add(
        RoleAssignment(
            user_id=uuid.UUID(da_user_id),
            role_id=da_role.id,
            university_id=test_university.id,
            scope_type=ScopeType.ACADEMIC_UNIT.value,
            scope_id=uuid.UUID(da_id),
        )
    )
    await db_session.commit()

    # Create Courses in Dept A and Dept B
    ca_res = client.post(
        "/api/v1/courses",
        headers=admin_headers,
        json={"code": f"CS1_{suffix}", "name": "CS Intro", "academic_unit_id": da_id},
    )
    ca_id = ca_res.json()["data"]["id"]

    cb_res = client.post(
        "/api/v1/courses",
        headers=admin_headers,
        json={"code": f"MT1_{suffix}", "name": "Calculus", "academic_unit_id": db_id},
    )
    cb_id = cb_res.json()["data"]["id"]

    _, semester_id, section_id, _ = setup_academic_prerequisites(client, admin_headers)
    room_id = create_test_room(client, admin_headers, suffix)

    off_a_res = client.post(
        "/api/v1/course-offerings",
        headers=admin_headers,
        json={"course_id": ca_id, "semester_id": semester_id, "section_id": section_id},
    )
    off_a_id = off_a_res.json()["data"]["id"]

    off_b_res = client.post(
        "/api/v1/course-offerings",
        headers=admin_headers,
        json={"course_id": cb_id, "semester_id": semester_id, "section_id": section_id},
    )
    off_b_id = off_b_res.json()["data"]["id"]

    # Occurrences
    tt_a = client.post(
        "/api/v1/timetables",
        headers=admin_headers,
        json={
            "course_offering_id": off_a_id,
            "room_id": room_id,
            "weekday": 7,
            "start_time": "08:00:00",
            "end_time": "09:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-10",
        },
    ).json()["data"]["id"]
    client.post(f"/api/v1/timetables/{tt_a}/generate-occurrences", headers=admin_headers)

    tt_b = client.post(
        "/api/v1/timetables",
        headers=admin_headers,
        json={
            "course_offering_id": off_b_id,
            "room_id": room_id,
            "weekday": 1,
            "start_time": "10:00:00",
            "end_time": "11:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-10",
        },
    ).json()["data"]["id"]
    client.post(f"/api/v1/timetables/{tt_b}/generate-occurrences", headers=admin_headers)

    occ_a_id = client.get(
        f"/api/v1/class-occurrences?course_offering_id={off_a_id}", headers=admin_headers
    ).json()["data"]["items"][0]["id"]
    occ_b_id = client.get(
        f"/api/v1/class-occurrences?course_offering_id={off_b_id}", headers=admin_headers
    ).json()["data"]["items"][0]["id"]

    # Dept A Admin headers
    da_headers = get_user_headers(client, da_name, da_pwd, str(test_university.id))

    # Dept A Admin CAN initialize session in Dept A
    sess_a = client.post(
        "/api/v1/attendance/sessions",
        headers=da_headers,
        json={"class_occurrence_id": occ_a_id, "activate_immediately": True},
    )
    assert sess_a.status_code == 201

    # Dept A Admin CANNOT initialize session in Dept B (sibling unit -> 403)
    sess_b = client.post(
        "/api/v1/attendance/sessions",
        headers=da_headers,
        json={"class_occurrence_id": occ_b_id, "activate_immediately": True},
    )
    assert sess_b.status_code == 403


@pytest.mark.asyncio
async def test_student_privacy_and_self_service(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify Student can query /me/attendance for own records but cannot access session rosters."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    suffix_1 = uuid.uuid4().hex[:6]
    suffix_2 = uuid.uuid4().hex[:6]

    # Create Student 1
    s1_user_id, s1_name, s1_pwd = create_test_user(client, admin_headers, prefix="s1")
    s1_prof = client.post(
        "/api/v1/students",
        headers=admin_headers,
        json={
            "user_id": s1_user_id,
            "student_number": f"ST1_{suffix_1}",
            "admission_date": "2024-09-01",
        },
    ).json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=admin_headers,
        json={"student_id": s1_prof},
    )

    # Create Student 2
    s2_user_id, s2_name, s2_pwd = create_test_user(client, admin_headers, prefix="s2")
    s2_prof = client.post(
        "/api/v1/students",
        headers=admin_headers,
        json={
            "user_id": s2_user_id,
            "student_number": f"ST2_{suffix_2}",
            "admission_date": "2024-09-01",
        },
    ).json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=admin_headers,
        json={"student_id": s2_prof},
    )

    # Assign STUDENT role to Student 1
    role_res = await db_session.execute(
        Role.__table__.select().where(Role.code == SystemRole.STUDENT.value)
    )
    stu_role = role_res.first()
    assert stu_role is not None

    db_session.add(
        RoleAssignment(
            user_id=uuid.UUID(s1_user_id),
            role_id=stu_role.id,
            university_id=test_university.id,
            scope_type=ScopeType.UNIVERSITY.value,
            scope_id=test_university.id,
        )
    )
    await db_session.commit()

    # Open attendance session & credit Student 1
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=admin_headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]

    client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/manual-credit",
        headers=admin_headers,
        json={"student_id": s1_prof, "reason": "Present in class"},
    )
    client.post(f"/api/v1/attendance/sessions/{session_id}/close", headers=admin_headers)

    # Student 1 logs in
    s1_headers = get_user_headers(client, s1_name, s1_pwd, str(test_university.id))

    # 1. Student 1 CAN read /me/attendance
    me_res = client.get("/api/v1/students/me/attendance", headers=s1_headers)
    assert me_res.status_code == 200
    my_records = me_res.json()["data"]
    assert len(my_records) == 1
    assert my_records[0]["session_id"] == session_id
    assert my_records[0]["start_credited"] is True

    # 2. Student 1 CANNOT view session-level admin roster records (403)
    roster_res = client.get(f"/api/v1/attendance/sessions/{session_id}/records", headers=s1_headers)
    assert roster_res.status_code == 403
