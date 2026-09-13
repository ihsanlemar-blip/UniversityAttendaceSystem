"""Test suite for Course Offerings, Lecturer Assignments, Student Enrollments, and Rosters."""

import uuid

from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_users import get_admin_headers


def setup_academic_prerequisites(
    client: TestClient, headers: dict[str, str]
) -> tuple[str, str, str, str]:
    """Helper to create Course, Academic Year, Semester, and Section."""
    suffix = uuid.uuid4().hex[:6]

    # Course
    c_res = client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "code": f"CS_{suffix}",
            "name": "Software Engineering",
            "credit_hours": 3,
        },
    )
    assert c_res.status_code == 201
    course_id = c_res.json()["data"]["id"]

    # Academic Year
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

    # Semester
    sem_res = client.post(
        "/api/v1/semesters",
        headers=headers,
        json={
            "academic_year_id": ay_id,
            "name": f"Semester {suffix}",
            "code": f"SEM_{suffix}",
            "sequence_order": 1,
            "start_date": "2026-09-01",
            "end_date": "2027-01-31",
        },
    )
    assert sem_res.status_code == 201
    semester_id = sem_res.json()["data"]["id"]

    # Section
    sec_res = client.post(
        "/api/v1/sections",
        headers=headers,
        json={
            "code": f"SEC_{suffix[:2].upper()}",
            "name": "Section Alpha",
            "semester_id": semester_id,
        },
    )
    assert sec_res.status_code == 201
    section_id = sec_res.json()["data"]["id"]

    return course_id, semester_id, section_id, ay_id


def test_course_offering_crud_and_uniqueness(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify course offering creation, uniqueness per semester/section, detail, and update."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers)

    # 1. Create Course Offering
    off_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={
            "course_id": course_id,
            "semester_id": semester_id,
            "section_id": section_id,
        },
    )
    assert off_res.status_code == 201
    off_data = off_res.json()["data"]
    offering_id = off_data["id"]
    assert off_data["course_id"] == course_id
    assert off_data["semester_id"] == semester_id
    assert off_data["section_id"] == section_id
    assert off_data["status"] == "ACTIVE"

    # 2. Duplicate Offering with same course, semester, and section rejected
    dup_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={
            "course_id": course_id,
            "semester_id": semester_id,
            "section_id": section_id,
        },
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "CONFLICT"

    # 3. Get Offering Detail
    get_res = client.get(f"/api/v1/course-offerings/{offering_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == offering_id
    assert get_res.json()["data"]["course_name"] == "Software Engineering"

    # 4. Update Offering status
    patch_res = client.patch(
        f"/api/v1/course-offerings/{offering_id}",
        headers=headers,
        json={"status": "COMPLETED"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == "COMPLETED"


def test_lecturer_assignment_and_single_primary_constraint(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify primary and co-teaching assignments, and single primary lecturer constraint."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers)

    # Create offering
    off_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={
            "course_id": course_id,
            "semester_id": semester_id,
            "section_id": section_id,
        },
    )
    offering_id = off_res.json()["data"]["id"]

    # Create Lecturer 1
    u1_id, u1_name, u1_pwd = create_test_user(client, headers, prefix="lec1")
    lec1_res = client.post(
        "/api/v1/lecturers",
        headers=headers,
        json={
            "user_id": u1_id,
            "employee_code": f"EMP_{uuid.uuid4().hex[:6].upper()}",
            "title": "Dr.",
        },
    )
    lec1_id = lec1_res.json()["data"]["id"]

    # Create Lecturer 2
    u2_id, _, _ = create_test_user(client, headers, prefix="lec2")
    lec2_res = client.post(
        "/api/v1/lecturers",
        headers=headers,
        json={
            "user_id": u2_id,
            "employee_code": f"EMP_{uuid.uuid4().hex[:6].upper()}",
            "title": "Mr.",
        },
    )
    lec2_id = lec2_res.json()["data"]["id"]

    # 1. Assign Lecturer 1 as Primary Lecturer
    assign1_res = client.post(
        f"/api/v1/course-offerings/{offering_id}/lecturers",
        headers=headers,
        json={
            "lecturer_id": lec1_id,
            "is_primary": True,
            "assignment_type": "PRIMARY",
        },
    )
    assert assign1_res.status_code == 201
    assign1_data = assign1_res.json()["data"]
    assert assign1_data["is_primary"] is True
    assert assign1_data["lecturer_id"] == lec1_id

    # 2. Attempt to assign Lecturer 2 as another Primary Lecturer must fail with 409 CONFLICT
    dup_primary_res = client.post(
        f"/api/v1/course-offerings/{offering_id}/lecturers",
        headers=headers,
        json={
            "lecturer_id": lec2_id,
            "is_primary": True,
            "assignment_type": "PRIMARY",
        },
    )
    assert dup_primary_res.status_code == 409
    assert dup_primary_res.json()["error"]["code"] == "CONFLICT"

    # 3. Assign Lecturer 2 as Co-Teacher (is_primary=False) succeeds
    assign2_res = client.post(
        f"/api/v1/course-offerings/{offering_id}/lecturers",
        headers=headers,
        json={
            "lecturer_id": lec2_id,
            "is_primary": False,
            "assignment_type": "CO_TEACHER",
        },
    )
    assert assign2_res.status_code == 201
    assert assign2_res.json()["data"]["is_primary"] is False

    # 4. Duplicate assignment of same lecturer rejected
    dup_assign_res = client.post(
        f"/api/v1/course-offerings/{offering_id}/lecturers",
        headers=headers,
        json={
            "lecturer_id": lec1_id,
            "is_primary": False,
            "assignment_type": "CO_TEACHER",
        },
    )
    assert dup_assign_res.status_code == 409
    assert dup_assign_res.json()["error"]["code"] == "CONFLICT"

    # 5. List lecturers on this offering via detail endpoint
    off_detail = client.get(
        f"/api/v1/course-offerings/{offering_id}",
        headers=headers,
    )
    assert off_detail.status_code == 200
    items = off_detail.json()["data"]["assigned_lecturers"]
    assert len(items) == 2

    # 6. Verify /lecturers/me/offerings for Lecturer 1
    lec1_headers = get_user_headers(client, u1_name, u1_pwd, str(test_university.id))
    my_off_res = client.get("/api/v1/lecturers/me/offerings", headers=lec1_headers)
    assert my_off_res.status_code == 200
    my_offerings = my_off_res.json()["data"]["items"]
    assert len(my_offerings) == 1
    assert my_offerings[0]["id"] == offering_id

    # 7. Unassign Lecturer 2
    del_res = client.delete(
        f"/api/v1/course-offerings/{offering_id}/lecturers/{lec2_id}",
        headers=headers,
    )
    assert del_res.status_code == 200

    # Detail again shows only Lecturer 1
    off_detail2 = client.get(
        f"/api/v1/course-offerings/{offering_id}",
        headers=headers,
    )
    assert len(off_detail2.json()["data"]["assigned_lecturers"]) == 1


def test_student_enrollment_and_drop_audit(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify student enrollment, duplicate rejection, drop preservation with dropped_at,
    and /students/me/enrollments.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers)

    # Offering
    off_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={
            "course_id": course_id,
            "semester_id": semester_id,
            "section_id": section_id,
        },
    )
    offering_id = off_res.json()["data"]["id"]

    # Student
    stu_u_id, stu_uname, stu_pwd = create_test_user(client, headers, prefix="stu_enr")
    stu_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={
            "user_id": stu_u_id,
            "student_number": f"ENR_{uuid.uuid4().hex[:6].upper()}",
        },
    )
    student_id = stu_res.json()["data"]["id"]

    # 1. Enroll Student
    enr_res = client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
        json={"student_id": student_id},
    )
    assert enr_res.status_code == 201
    enr_data = enr_res.json()["data"]
    enr_id = enr_data["id"]
    assert enr_data["status"] == "ACTIVE"
    assert enr_data["dropped_at"] is None
    assert enr_data["student_id"] == student_id

    # 2. Duplicate active enrollment rejected with CONFLICT
    dup_enr = client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
        json={"student_id": student_id},
    )
    assert dup_enr.status_code == 409
    assert dup_enr.json()["error"]["code"] == "CONFLICT"

    # 3. Query roster
    roster_res = client.get(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
    )
    assert roster_res.status_code == 200
    roster = roster_res.json()["data"]["items"]
    assert len(roster) == 1
    assert roster[0]["student_id"] == student_id
    assert roster[0]["student_name"] == stu_uname

    # 4. Verify /students/me/enrollments
    stu_headers = get_user_headers(client, stu_uname, stu_pwd, str(test_university.id))
    my_enr_res = client.get("/api/v1/students/me/enrollments", headers=stu_headers)
    assert my_enr_res.status_code == 200
    my_enrs = my_enr_res.json()["data"]
    assert len(my_enrs) == 1
    assert my_enrs[0]["course_offering_id"] == offering_id

    # 5. Drop enrollment
    drop_res = client.delete(
        f"/api/v1/course-offerings/{offering_id}/enrollments/{student_id}",
        headers=headers,
    )
    assert drop_res.status_code == 200
    drop_data = drop_res.json()["data"]
    assert drop_data["status"] == "DROPPED"
    assert drop_data["dropped_at"] is not None
    assert drop_data["id"] == enr_id

    # 6. Roster still retains the dropped record with status DROPPED (audit history preserved)
    roster2_res = client.get(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
    )
    assert roster2_res.status_code == 200
    roster2 = roster2_res.json()["data"]["items"]
    assert len(roster2) == 1
    assert roster2[0]["status"] == "DROPPED"
    assert roster2[0]["dropped_at"] is not None

    # Filtering by ACTIVE returns empty
    roster_act = client.get(
        f"/api/v1/course-offerings/{offering_id}/enrollments?status=ACTIVE",
        headers=headers,
    )
    assert len(roster_act.json()["data"]["items"]) == 0

    # 7. Re-enrollment reactivates the same canonical row instead of creating duplicate
    re_enr_res = client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
        json={"student_id": student_id},
    )
    assert re_enr_res.status_code == 201
    re_enr_data = re_enr_res.json()["data"]
    assert re_enr_data["id"] == enr_id
    assert re_enr_data["status"] == "ACTIVE"
    assert re_enr_data["dropped_at"] is None

    # Verify total enrollment rows in roster is still exactly 1
    roster3_res = client.get(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
    )
    assert roster3_res.status_code == 200
    roster3 = roster3_res.json()["data"]["items"]
    assert len(roster3) == 1
    assert roster3[0]["id"] == enr_id
    assert roster3[0]["status"] == "ACTIVE"


def test_batch_enrollment_and_reactivation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify batch enrollment, partial drop, and batch re-enrollment reactivation."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers)

    # Offering
    off_res = client.post(
        "/api/v1/course-offerings",
        headers=headers,
        json={
            "course_id": course_id,
            "semester_id": semester_id,
            "section_id": section_id,
        },
    )
    offering_id = off_res.json()["data"]["id"]

    # 3 Students
    student_ids = []
    for i in range(3):
        u_id, _, _ = create_test_user(client, headers, prefix=f"bat_{i}")
        s_res = client.post(
            "/api/v1/students",
            headers=headers,
            json={
                "user_id": u_id,
                "student_number": f"BAT_{uuid.uuid4().hex[:6].upper()}",
            },
        )
        assert s_res.status_code == 201
        student_ids.append(s_res.json()["data"]["id"])

    # 1. Batch enroll all 3
    batch_res1 = client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments/batch",
        headers=headers,
        json={"student_ids": student_ids},
    )
    assert batch_res1.status_code == 201
    enrolled_items = batch_res1.json()["data"]
    assert len(enrolled_items) == 3
    initial_ids = {e["student_id"]: e["id"] for e in enrolled_items}

    # 2. Drop student 1
    drop_res = client.delete(
        f"/api/v1/course-offerings/{offering_id}/enrollments/{student_ids[1]}",
        headers=headers,
    )
    assert drop_res.status_code == 200
    assert drop_res.json()["data"]["status"] == "DROPPED"

    # 3. Batch re-enroll student 1 and student 2
    batch_res2 = client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments/batch",
        headers=headers,
        json={"student_ids": [student_ids[1], student_ids[2]]},
    )
    assert batch_res2.status_code == 201

    # 4. Check roster: all 3 students are ACTIVE, and student 1 kept the exact same canonical ID
    roster_res = client.get(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
    )
    assert roster_res.status_code == 200
    items = roster_res.json()["data"]["items"]
    assert len(items) == 3
    for it in items:
        assert it["status"] == "ACTIVE"
        assert it["id"] == initial_ids[it["student_id"]]
