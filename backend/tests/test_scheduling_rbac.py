"""Test suite for Lecturer & Student personal schedules, scoped RBAC, and tenant isolation."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.passwords import hash_password
from backend.app.core.constants import ScopeType, SystemRole, UserStatus
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_offerings import setup_academic_prerequisites
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_timetables import create_test_room
from backend.tests.test_users import get_admin_headers


def test_lecturer_and_student_personal_schedules(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Lecturer and Student personal schedule self-views return only assigned
    or enrolled classes.
    """
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, admin_headers)
    suffix = uuid.uuid4().hex[:6]
    room_id = create_test_room(client, admin_headers, suffix)

    # 1. Create Offering 1
    off1_res = client.post(
        "/api/v1/course-offerings",
        headers=admin_headers,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    off1_id = off1_res.json()["data"]["id"]

    # 2. Create Offering 2 (Different course)
    c2_res = client.post(
        "/api/v1/courses",
        headers=admin_headers,
        json={"code": f"C2_{suffix}", "name": "Calculus", "credit_hours": 3},
    )
    c2_id = c2_res.json()["data"]["id"]
    off2_res = client.post(
        "/api/v1/course-offerings",
        headers=admin_headers,
        json={"course_id": c2_id, "semester_id": semester_id, "section_id": section_id},
    )
    off2_id = off2_res.json()["data"]["id"]

    # 3. Create Lecturer User & Profile
    lec_user_id, lec_uname, lec_pwd = create_test_user(client, admin_headers, prefix="lec")
    lec_res = client.post(
        "/api/v1/lecturers",
        headers=admin_headers,
        json={"user_id": lec_user_id, "employee_code": f"LEC_{suffix}"},
    )
    lec_id = lec_res.json()["data"]["id"]

    # Assign Lecturer to Offering 1 ONLY
    client.post(
        f"/api/v1/course-offerings/{off1_id}/lecturers",
        headers=admin_headers,
        json={"lecturer_id": lec_id, "is_primary": True},
    )

    # 4. Create Student User & Profile
    stu_user_id, stu_uname, stu_pwd = create_test_user(client, admin_headers, prefix="stu")
    stu_res = client.post(
        "/api/v1/students",
        headers=admin_headers,
        json={"user_id": stu_user_id, "student_number": f"STU_{suffix}"},
    )
    stu_id = stu_res.json()["data"]["id"]

    # Enroll Student in Offering 1 ONLY
    client.post(
        f"/api/v1/course-offerings/{off1_id}/enrollments",
        headers=admin_headers,
        json={"student_id": stu_id},
    )

    # 5. Create Timetable rules and generate occurrences for BOTH offerings
    tt1_res = client.post(
        "/api/v1/timetables",
        headers=admin_headers,
        json={
            "course_offering_id": off1_id,
            "room_id": room_id,
            "weekday": 7,  # Sunday
            "start_time": "08:00:00",
            "end_time": "09:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-15",
        },
    )
    tt1_id = tt1_res.json()["data"]["id"]
    client.post(f"/api/v1/timetables/{tt1_id}/generate-occurrences", headers=admin_headers)

    tt2_res = client.post(
        "/api/v1/timetables",
        headers=admin_headers,
        json={
            "course_offering_id": off2_id,
            "weekday": 1,  # Monday
            "start_time": "10:00:00",
            "end_time": "11:30:00",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-15",
        },
    )
    tt2_id = tt2_res.json()["data"]["id"]
    client.post(f"/api/v1/timetables/{tt2_id}/generate-occurrences", headers=admin_headers)

    # 6. Check Lecturer personal schedule self-view
    lec_headers = get_user_headers(client, lec_uname, lec_pwd, str(test_university.id))
    lec_sched_res = client.get("/api/v1/lecturers/me/class-occurrences", headers=lec_headers)
    assert lec_sched_res.status_code == 200
    lec_items = lec_sched_res.json()["data"]
    # Should only contain Offering 1 occurrences (Sunday meetings)
    assert len(lec_items) > 0
    assert all(item["course_offering_id"] == off1_id for item in lec_items)

    # 7. Check Student personal schedule self-view
    stu_headers = get_user_headers(client, stu_uname, stu_pwd, str(test_university.id))
    stu_sched_res = client.get("/api/v1/students/me/class-occurrences", headers=stu_headers)
    assert stu_sched_res.status_code == 200
    stu_items = stu_sched_res.json()["data"]
    # Should only contain Offering 1 occurrences
    assert len(stu_items) > 0
    assert all(item["course_offering_id"] == off1_id for item in stu_items)

    # 8. Drop student from Offering 1 -> Student schedule becomes empty!
    client.delete(f"/api/v1/course-offerings/{off1_id}/enrollments/{stu_id}", headers=admin_headers)
    stu_after_drop = client.get("/api/v1/students/me/class-occurrences", headers=stu_headers)
    assert stu_after_drop.status_code == 200
    assert len(stu_after_drop.json()["data"]) == 0


@pytest.mark.asyncio
async def test_faculty_admin_scoped_timetable_authorization(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Faculty Admin can manage timetables in assigned subtree,
    but denied sibling faculty.
    """
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Create Faculty A and Faculty B (siblings)
    fa_res = client.post(
        "/api/v1/academic-units",
        headers=admin_headers,
        json={"name": "Engineering Faculty", "code": f"ENG_{suffix}", "unit_type": "FACULTY"},
    )
    assert fa_res.status_code == 201
    fa_id = fa_res.json()["data"]["id"]

    fb_res = client.post(
        "/api/v1/academic-units",
        headers=admin_headers,
        json={"name": "Law Faculty", "code": f"LAW_{suffix}", "unit_type": "FACULTY"},
    )
    assert fb_res.status_code == 201
    fb_id = fb_res.json()["data"]["id"]

    # Create Faculty Admin user assigned scoped to Faculty A
    fa_user = User(
        university_id=test_university.id,
        username=f"fa_admin_{suffix}",
        password_hash=hash_password("FacAdminSecure123!"),
        email=f"fa_{suffix}@university.edu",
        status=UserStatus.ACTIVE.value,
    )
    db_session.add(fa_user)
    await db_session.flush()

    role_res = await db_session.execute(
        Role.__table__.select().where(Role.code == SystemRole.FACULTY_ADMIN.value)
    )
    role_row = role_res.first()
    assert role_row is not None

    db_session.add(
        RoleAssignment(
            user_id=fa_user.id,
            role_id=role_row.id,
            university_id=test_university.id,
            scope_type=ScopeType.ACADEMIC_UNIT.value,
            scope_id=uuid.UUID(fa_id),
        )
    )
    await db_session.commit()

    # Create courses in Faculty A and Faculty B
    ca_res = client.post(
        "/api/v1/courses",
        headers=admin_headers,
        json={"code": f"EE_{suffix}", "name": "Circuits", "academic_unit_id": fa_id},
    )
    ca_id = ca_res.json()["data"]["id"]

    cb_res = client.post(
        "/api/v1/courses",
        headers=admin_headers,
        json={"code": f"LAW_{suffix}", "name": "Civil Law", "academic_unit_id": fb_id},
    )
    cb_id = cb_res.json()["data"]["id"]

    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, admin_headers)

    # Offering in Faculty A
    off_a = client.post(
        "/api/v1/course-offerings",
        headers=admin_headers,
        json={"course_id": ca_id, "semester_id": semester_id, "academic_unit_id": fa_id},
    )
    off_a_id = off_a.json()["data"]["id"]

    # Offering in Faculty B
    off_b = client.post(
        "/api/v1/course-offerings",
        headers=admin_headers,
        json={"course_id": cb_id, "semester_id": semester_id, "academic_unit_id": fb_id},
    )
    off_b_id = off_b.json()["data"]["id"]

    # Log in as Faculty Admin of Faculty A
    fa_headers = get_user_headers(
        client, fa_user.username, "FacAdminSecure123!", str(test_university.id)
    )

    # 1. Manage timetable in Faculty A -> ALLOWED (201)
    tt_a_res = client.post(
        "/api/v1/timetables",
        headers=fa_headers,
        json={
            "course_offering_id": off_a_id,
            "weekday": 7,
            "start_time": "08:00:00",
            "end_time": "09:30:00",
        },
    )
    assert tt_a_res.status_code == 201

    # 2. Manage timetable in Faculty B (sibling faculty) -> DENIED (403)
    tt_b_res = client.post(
        "/api/v1/timetables",
        headers=fa_headers,
        json={
            "course_offering_id": off_b_id,
            "weekday": 7,
            "start_time": "08:00:00",
            "end_time": "09:30:00",
        },
    )
    assert tt_b_res.status_code == 403
    assert tt_b_res.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_department_admin_scoped_timetable_authorization(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Department Admin can manage timetables in assigned department,

    but is denied for sibling departments.
    """
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Create Parent Faculty
    f_res = client.post(
        "/api/v1/academic-units",
        headers=admin_headers,
        json={"name": "Science Faculty", "code": f"SCI_{suffix}", "unit_type": "FACULTY"},
    )
    assert f_res.status_code == 201
    f_id = f_res.json()["data"]["id"]

    # Create Dept A (Computer Science) and Dept B (Mathematics)
    da_res = client.post(
        "/api/v1/academic-units",
        headers=admin_headers,
        json={
            "name": "CS Dept",
            "code": f"CS_{suffix}",
            "unit_type": "DEPARTMENT",
            "parent_id": f_id,
        },
    )
    assert da_res.status_code == 201
    da_id = da_res.json()["data"]["id"]

    db_res = client.post(
        "/api/v1/academic-units",
        headers=admin_headers,
        json={
            "name": "Math Dept",
            "code": f"MATH_{suffix}",
            "unit_type": "DEPARTMENT",
            "parent_id": f_id,
        },
    )
    assert db_res.status_code == 201
    db_id = db_res.json()["data"]["id"]

    # Create Department Admin user assigned to Dept A
    da_user = User(
        university_id=test_university.id,
        username=f"da_admin_{suffix}",
        password_hash=hash_password("DeptAdminPass123!"),
        email=f"da_{suffix}@university.edu",
        status=UserStatus.ACTIVE.value,
    )
    db_session.add(da_user)
    await db_session.flush()

    role_res = await db_session.execute(
        Role.__table__.select().where(Role.code == SystemRole.DEPARTMENT_ADMIN.value)
    )
    role_row = role_res.first()
    assert role_row is not None

    db_session.add(
        RoleAssignment(
            user_id=da_user.id,
            role_id=role_row.id,
            university_id=test_university.id,
            scope_type=ScopeType.ACADEMIC_UNIT.value,
            scope_id=uuid.UUID(da_id),
        )
    )
    await db_session.commit()

    # Create courses in Dept A and Dept B
    ca_res = client.post(
        "/api/v1/courses",
        headers=admin_headers,
        json={"code": f"CS1_{suffix}", "name": "Intro CS", "academic_unit_id": da_id},
    )
    ca_id = ca_res.json()["data"]["id"]

    cb_res = client.post(
        "/api/v1/courses",
        headers=admin_headers,
        json={"code": f"MTH_{suffix}", "name": "Linear Algebra", "academic_unit_id": db_id},
    )
    cb_id = cb_res.json()["data"]["id"]

    _, semester_id, _, _ = setup_academic_prerequisites(client, admin_headers)

    # Offering in Dept A
    off_a = client.post(
        "/api/v1/course-offerings",
        headers=admin_headers,
        json={"course_id": ca_id, "semester_id": semester_id, "academic_unit_id": da_id},
    )
    off_a_id = off_a.json()["data"]["id"]

    # Offering in Dept B
    off_b = client.post(
        "/api/v1/course-offerings",
        headers=admin_headers,
        json={"course_id": cb_id, "semester_id": semester_id, "academic_unit_id": db_id},
    )
    off_b_id = off_b.json()["data"]["id"]

    # Log in as Department Admin of Dept A
    da_headers = get_user_headers(
        client, da_user.username, "DeptAdminPass123!", str(test_university.id)
    )

    # 1. Manage timetable in Dept A -> ALLOWED (201)
    tt_a_res = client.post(
        "/api/v1/timetables",
        headers=da_headers,
        json={
            "course_offering_id": off_a_id,
            "weekday": 1,
            "start_time": "08:00:00",
            "end_time": "09:30:00",
        },
    )
    assert tt_a_res.status_code == 201

    # 2. Manage timetable in Dept B (sibling department) -> DENIED (403)
    tt_b_res = client.post(
        "/api/v1/timetables",
        headers=da_headers,
        json={
            "course_offering_id": off_b_id,
            "weekday": 1,
            "start_time": "08:00:00",
            "end_time": "09:30:00",
        },
    )
    assert tt_b_res.status_code == 403
    assert tt_b_res.json()["error"]["code"] == "PERMISSION_DENIED"
