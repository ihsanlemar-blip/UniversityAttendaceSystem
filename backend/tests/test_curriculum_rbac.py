"""Test suite for curriculum, roster, and offering RBAC permissions and subtree scoping."""

import uuid

from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_offerings import setup_academic_prerequisites
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_users import get_admin_headers


def test_faculty_admin_subtree_scoping(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Faculty Admin can manage courses and students within their faculty subtree,
    but is forbidden in other faculties.
    """
    headers_admin = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Create Faculty A and child Department A1
    fac_a_res = client.post(
        "/api/v1/academic-units",
        headers=headers_admin,
        json={"name": "Engineering Faculty", "code": f"ENG_{suffix}", "unit_type": "FACULTY"},
    )
    assert fac_a_res.status_code == 201
    fac_a_id = fac_a_res.json()["data"]["id"]

    dept_a1_res = client.post(
        "/api/v1/academic-units",
        headers=headers_admin,
        json={
            "name": "Software Engineering Dept",
            "code": f"CS_{suffix}",
            "unit_type": "DEPARTMENT",
            "parent_id": fac_a_id,
        },
    )
    assert dept_a1_res.status_code == 201
    dept_a1_id = dept_a1_res.json()["data"]["id"]

    # Create Faculty B (sibling subtree)
    fac_b_res = client.post(
        "/api/v1/academic-units",
        headers=headers_admin,
        json={"name": "Medical Faculty", "code": f"MED_{suffix}", "unit_type": "FACULTY"},
    )
    assert fac_b_res.status_code == 201
    fac_b_id = fac_b_res.json()["data"]["id"]

    # Create Faculty Admin user for Faculty A
    u_id, u_name, u_pwd = create_test_user(client, headers_admin, prefix="fac_admin")

    # We need to assign FACULTY_ADMIN role scoped to Faculty A
    roles_res = client.get("/api/v1/roles", headers=headers_admin)
    assert roles_res.status_code == 200
    fac_role_id = next(r["id"] for r in roles_res.json()["data"] if r["code"] == "FACULTY_ADMIN")

    assign_res = client.post(
        f"/api/v1/users/{u_id}/role-assignments",
        headers=headers_admin,
        json={
            "role_id": fac_role_id,
            "scope_type": "ACADEMIC_UNIT",
            "scope_id": fac_a_id,
        },
    )
    assert assign_res.status_code == 201

    headers_fac_admin = get_user_headers(client, u_name, u_pwd, str(test_university.id))

    # 1. Faculty Admin CAN create course in Faculty A
    c_ok1 = client.post(
        "/api/v1/courses",
        headers=headers_fac_admin,
        json={
            "code": f"ENG101_{suffix}",
            "name": "Intro to Engineering",
            "academic_unit_id": fac_a_id,
            "credit_hours": 3,
        },
    )
    assert c_ok1.status_code == 201

    # 2. Faculty Admin CAN create course in Department A1 (child of Faculty A)
    c_ok2 = client.post(
        "/api/v1/courses",
        headers=headers_fac_admin,
        json={
            "code": f"CS101_{suffix}",
            "name": "Algorithms I",
            "academic_unit_id": dept_a1_id,
            "credit_hours": 4,
        },
    )
    assert c_ok2.status_code == 201

    # 3. Faculty Admin CANNOT create course in Faculty B (sibling subtree -> 403)
    c_forbidden = client.post(
        "/api/v1/courses",
        headers=headers_fac_admin,
        json={
            "code": f"MED101_{suffix}",
            "name": "Anatomy",
            "academic_unit_id": fac_b_id,
            "credit_hours": 3,
        },
    )
    assert c_forbidden.status_code == 403
    assert c_forbidden.json()["error"]["code"] == "PERMISSION_DENIED"

    # 4. Faculty Admin CANNOT create student under Faculty B
    stu_u_id, _, _ = create_test_user(client, headers_admin, prefix="stu_b")
    stu_forbidden = client.post(
        "/api/v1/students",
        headers=headers_fac_admin,
        json={
            "user_id": stu_u_id,
            "student_number": f"STU_MED_{uuid.uuid4().hex[:6].upper()}",
            "academic_unit_id": fac_b_id,
        },
    )
    assert stu_forbidden.status_code == 403
    assert stu_forbidden.json()["error"]["code"] == "PERMISSION_DENIED"


def test_auditor_read_only_access(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Auditor role can view catalog and people but cannot perform mutations."""
    headers_admin = get_admin_headers(client, test_admin_user, test_university)
    u_id, u_name, u_pwd = create_test_user(client, headers_admin, prefix="audit")

    roles_res = client.get("/api/v1/roles", headers=headers_admin)
    assert roles_res.status_code == 200
    auditor_role_id = next(r["id"] for r in roles_res.json()["data"] if r["code"] == "AUDITOR")

    assign_res = client.post(
        f"/api/v1/users/{u_id}/role-assignments",
        headers=headers_admin,
        json={
            "role_id": auditor_role_id,
            "scope_type": "UNIVERSITY",
            "scope_id": str(test_university.id),
        },
    )
    assert assign_res.status_code == 201

    headers_auditor = get_user_headers(client, u_name, u_pwd, str(test_university.id))

    # 1. Auditor CAN read courses
    get_c = client.get("/api/v1/courses", headers=headers_auditor)
    assert get_c.status_code == 200

    # 2. Auditor CAN read students
    get_s = client.get("/api/v1/students", headers=headers_auditor)
    assert get_s.status_code == 200

    # 3. Auditor CAN read lecturers
    get_l = client.get("/api/v1/lecturers", headers=headers_auditor)
    assert get_l.status_code == 200

    # 4. Auditor CAN read course offerings
    get_o = client.get("/api/v1/course-offerings", headers=headers_auditor)
    assert get_o.status_code == 200

    # 5. Auditor CANNOT mutate courses -> 403
    c_mut = client.post(
        "/api/v1/courses",
        headers=headers_auditor,
        json={"code": f"AUD_{uuid.uuid4().hex[:6]}", "name": "Fail Course"},
    )
    assert c_mut.status_code == 403

    # 6. Auditor CANNOT mutate students -> 403
    s_mut = client.post(
        "/api/v1/students",
        headers=headers_auditor,
        json={"user_id": str(uuid.uuid4()), "student_number": "AUD_STU"},
    )
    assert s_mut.status_code == 403


def test_student_forbidden_mutations(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Student role cannot create courses, offerings, or enrollments."""
    headers_admin = get_admin_headers(client, test_admin_user, test_university)
    u_id, u_name, u_pwd = create_test_user(client, headers_admin, prefix="stu_role")

    roles_res = client.get("/api/v1/roles", headers=headers_admin)
    assert roles_res.status_code == 200
    student_role_id = next(r["id"] for r in roles_res.json()["data"] if r["code"] == "STUDENT")

    assign_res = client.post(
        f"/api/v1/users/{u_id}/role-assignments",
        headers=headers_admin,
        json={
            "role_id": student_role_id,
            "scope_type": "UNIVERSITY",
            "scope_id": str(test_university.id),
        },
    )
    assert assign_res.status_code == 201

    headers_stu = get_user_headers(client, u_name, u_pwd, str(test_university.id))

    # Cannot create course -> 403
    c_res = client.post(
        "/api/v1/courses",
        headers=headers_stu,
        json={"code": "FORBIDDEN", "name": "Forbidden Course"},
    )
    assert c_res.status_code == 403

    # Cannot create course offering -> 403
    off_res = client.post(
        "/api/v1/course-offerings",
        headers=headers_stu,
        json={
            "course_id": str(uuid.uuid4()),
            "semester_id": str(uuid.uuid4()),
        },
    )
    assert off_res.status_code == 403


def test_department_admin_cannot_access_sibling_department(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Department Admin can manage within their department,
    but is strictly forbidden in sibling departments.
    """
    headers_admin = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Create Faculty
    fac_res = client.post(
        "/api/v1/academic-units",
        headers=headers_admin,
        json={"name": "Science Faculty", "code": f"SCI_{suffix}", "unit_type": "FACULTY"},
    )
    assert fac_res.status_code == 201
    fac_id = fac_res.json()["data"]["id"]

    # Create Dept 1 (Mathematics)
    d1_res = client.post(
        "/api/v1/academic-units",
        headers=headers_admin,
        json={
            "name": "Math Dept",
            "code": f"MATH_{suffix}",
            "unit_type": "DEPARTMENT",
            "parent_id": fac_id,
        },
    )
    assert d1_res.status_code == 201
    d1_id = d1_res.json()["data"]["id"]

    # Create Dept 2 (Physics - sibling)
    d2_res = client.post(
        "/api/v1/academic-units",
        headers=headers_admin,
        json={
            "name": "Physics Dept",
            "code": f"PHYS_{suffix}",
            "unit_type": "DEPARTMENT",
            "parent_id": fac_id,
        },
    )
    assert d2_res.status_code == 201
    d2_id = d2_res.json()["data"]["id"]

    # Create Dept Admin user for Dept 1
    u_id, u_name, u_pwd = create_test_user(client, headers_admin, prefix="dept_adm")
    roles_res = client.get("/api/v1/roles", headers=headers_admin)
    dept_role_id = next(
        r["id"] for r in roles_res.json()["data"] if r["code"] == "DEPARTMENT_ADMIN"
    )

    assign_res = client.post(
        f"/api/v1/users/{u_id}/role-assignments",
        headers=headers_admin,
        json={
            "role_id": dept_role_id,
            "scope_type": "ACADEMIC_UNIT",
            "scope_id": d1_id,
        },
    )
    assert assign_res.status_code == 201
    headers_dept_adm = get_user_headers(client, u_name, u_pwd, str(test_university.id))

    # 1. Dept 1 Admin CAN create course in Dept 1
    c_ok = client.post(
        "/api/v1/courses",
        headers=headers_dept_adm,
        json={
            "code": f"MTH101_{suffix}",
            "name": "Calculus I",
            "academic_unit_id": d1_id,
            "credit_hours": 3,
        },
    )
    assert c_ok.status_code == 201

    # 2. Dept 1 Admin CANNOT create course in Sibling Dept 2 -> 403
    c_forbidden = client.post(
        "/api/v1/courses",
        headers=headers_dept_adm,
        json={
            "code": f"PHY101_{suffix}",
            "name": "Mechanics",
            "academic_unit_id": d2_id,
            "credit_hours": 3,
        },
    )
    assert c_forbidden.status_code == 403
    assert c_forbidden.json()["error"]["code"] == "PERMISSION_DENIED"

    # 3. Dept 1 Admin CANNOT create section in Sibling Dept 2 -> 403
    sec_forbidden = client.post(
        "/api/v1/sections",
        headers=headers_dept_adm,
        json={"code": f"S_{suffix[:2].upper()}", "name": "Section P", "academic_unit_id": d2_id},
    )
    assert sec_forbidden.status_code == 403
    assert sec_forbidden.json()["error"]["code"] == "PERMISSION_DENIED"

    # 4. Dept 1 Admin CANNOT create student in Sibling Dept 2 -> 403
    stu_u_id, _, _ = create_test_user(client, headers_admin, prefix="stu_d2")
    stu_forbidden = client.post(
        "/api/v1/students",
        headers=headers_dept_adm,
        json={
            "user_id": stu_u_id,
            "student_number": f"STU_D2_{uuid.uuid4().hex[:6].upper()}",
            "academic_unit_id": d2_id,
        },
    )
    assert stu_forbidden.status_code == 403
    assert stu_forbidden.json()["error"]["code"] == "PERMISSION_DENIED"


def test_cross_university_tenant_isolation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    second_university: University,
    second_admin_user: User,
) -> None:
    """Verify strict tenant isolation: University A admin cannot access or mutate
    University B entities.
    """
    headers_a = get_admin_headers(client, test_admin_user, test_university)
    headers_b = get_admin_headers(client, second_admin_user, second_university)
    suffix = uuid.uuid4().hex[:6]

    # Create Course, Student, Lecturer, Offering in University B
    c_b_res = client.post(
        "/api/v1/courses",
        headers=headers_b,
        json={"code": f"UB_{suffix}", "name": "Univ B Course", "credit_hours": 3},
    )
    assert c_b_res.status_code == 201
    course_b_id = c_b_res.json()["data"]["id"]

    stu_b_uid, _, _ = create_test_user(client, headers_b, prefix="ub_stu")
    stu_b_res = client.post(
        "/api/v1/students",
        headers=headers_b,
        json={"user_id": stu_b_uid, "student_number": f"UBS_{suffix.upper()}"},
    )
    assert stu_b_res.status_code == 201
    student_b_id = stu_b_res.json()["data"]["id"]

    lec_b_uid, _, _ = create_test_user(client, headers_b, prefix="ub_lec")
    lec_b_res = client.post(
        "/api/v1/lecturers",
        headers=headers_b,
        json={"user_id": lec_b_uid, "employee_code": f"UBL_{suffix.upper()}"},
    )
    assert lec_b_res.status_code == 201
    lecturer_b_id = lec_b_res.json()["data"]["id"]

    # Semester in Univ B
    ay_b_res = client.post(
        "/api/v1/academic-years",
        headers=headers_b,
        json={
            "name": f"AY B {suffix}",
            "code": f"AYB_{suffix}",
            "start_date": "2026-09-01",
            "end_date": "2027-06-30",
        },
    )
    assert ay_b_res.status_code == 201
    ay_b_id = ay_b_res.json()["data"]["id"]

    sem_b_res = client.post(
        "/api/v1/semesters",
        headers=headers_b,
        json={
            "academic_year_id": ay_b_id,
            "name": f"Sem B {suffix}",
            "code": f"SEMB_{suffix}",
            "sequence_order": 1,
            "start_date": "2026-09-01",
            "end_date": "2027-01-31",
        },
    )
    assert sem_b_res.status_code == 201
    sem_b_id = sem_b_res.json()["data"]["id"]

    off_b_res = client.post(
        "/api/v1/course-offerings",
        headers=headers_b,
        json={"course_id": course_b_id, "semester_id": sem_b_id},
    )
    assert off_b_res.status_code == 201
    offering_b_id = off_b_res.json()["data"]["id"]

    # Now, University A caller attempts cross-tenant access -> Must return 404 NOT_FOUND
    # 1. Course
    get_c = client.get(f"/api/v1/courses/{course_b_id}", headers=headers_a)
    assert get_c.status_code == 404
    assert get_c.json()["error"]["code"] == "NOT_FOUND"

    patch_c = client.patch(
        f"/api/v1/courses/{course_b_id}", headers=headers_a, json={"name": "Hacked"}
    )
    assert patch_c.status_code == 404

    del_c = client.delete(f"/api/v1/courses/{course_b_id}", headers=headers_a)
    assert del_c.status_code == 404

    # 2. Student
    get_s = client.get(f"/api/v1/students/{student_b_id}", headers=headers_a)
    assert get_s.status_code == 404

    # 3. Lecturer
    get_l = client.get(f"/api/v1/lecturers/{lecturer_b_id}", headers=headers_a)
    assert get_l.status_code == 404

    # 4. Offering
    get_o = client.get(f"/api/v1/course-offerings/{offering_b_id}", headers=headers_a)
    assert get_o.status_code == 404

    roster_o = client.get(
        f"/api/v1/course-offerings/{offering_b_id}/enrollments", headers=headers_a
    )
    assert roster_o.status_code == 404


def test_student_cannot_read_another_student_enrollment(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Student cannot read other students' enrollments or class rosters."""
    headers_admin = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers_admin)

    off_res = client.post(
        "/api/v1/course-offerings",
        headers=headers_admin,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    offering_id = off_res.json()["data"]["id"]

    # Student 1
    u1_id, u1_name, u1_pwd = create_test_user(client, headers_admin, prefix="s1")
    s1_res = client.post(
        "/api/v1/students",
        headers=headers_admin,
        json={"user_id": u1_id, "student_number": f"S1_{uuid.uuid4().hex[:6].upper()}"},
    )
    s1_id = s1_res.json()["data"]["id"]

    # Student 2
    u2_id, _, _ = create_test_user(client, headers_admin, prefix="s2")
    s2_res = client.post(
        "/api/v1/students",
        headers=headers_admin,
        json={"user_id": u2_id, "student_number": f"S2_{uuid.uuid4().hex[:6].upper()}"},
    )
    s2_id = s2_res.json()["data"]["id"]

    # Assign STUDENT role to Student 1
    roles_res = client.get("/api/v1/roles", headers=headers_admin)
    student_role_id = next(r["id"] for r in roles_res.json()["data"] if r["code"] == "STUDENT")
    client.post(
        f"/api/v1/users/{u1_id}/role-assignments",
        headers=headers_admin,
        json={
            "role_id": student_role_id,
            "scope_type": "UNIVERSITY",
            "scope_id": str(test_university.id),
        },
    )

    # Enroll both in offering
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers_admin,
        json={"student_id": s1_id},
    )
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers_admin,
        json={"student_id": s2_id},
    )

    # Student 1 headers
    headers_s1 = get_user_headers(client, u1_name, u1_pwd, str(test_university.id))

    # 1. Student 1 /me/enrollments contains ONLY Student 1's enrollment
    my_enrs = client.get("/api/v1/students/me/enrollments", headers=headers_s1)
    assert my_enrs.status_code == 200
    items = my_enrs.json()["data"]
    assert len(items) == 1
    assert items[0]["course_offering_id"] == offering_id

    # 2. Student 1 CANNOT view full roster -> 403
    roster_res = client.get(
        f"/api/v1/course-offerings/{offering_id}/enrollments", headers=headers_s1
    )
    assert roster_res.status_code == 403
    assert roster_res.json()["error"]["code"] == "PERMISSION_DENIED"

    # 3. Student 1 CANNOT view Student 2 profile -> 403
    s2_profile = client.get(f"/api/v1/students/{s2_id}", headers=headers_s1)
    assert s2_profile.status_code == 403


def test_lecturer_cannot_access_unassigned_offering(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Lecturer cannot access or manage offerings they are not assigned to."""
    headers_admin = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers_admin)

    # Offering 1 & Offering 2
    off1 = client.post(
        "/api/v1/course-offerings",
        headers=headers_admin,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    ).json()["data"]["id"]

    suffix = uuid.uuid4().hex[:6]
    c2 = client.post(
        "/api/v1/courses",
        headers=headers_admin,
        json={"code": f"C2_{suffix}", "name": "Course 2", "credit_hours": 3},
    ).json()["data"]["id"]
    off2 = client.post(
        "/api/v1/course-offerings",
        headers=headers_admin,
        json={"course_id": c2, "semester_id": semester_id},
    ).json()["data"]["id"]

    # Lecturer 1 and Lecturer 2
    l1_uid, _, _ = create_test_user(client, headers_admin, prefix="l1")
    l1_id = client.post(
        "/api/v1/lecturers",
        headers=headers_admin,
        json={"user_id": l1_uid, "employee_code": f"L1_{suffix.upper()}"},
    ).json()["data"]["id"]

    l2_uid, l2_uname, l2_pwd = create_test_user(client, headers_admin, prefix="l2")
    l2_id = client.post(
        "/api/v1/lecturers",
        headers=headers_admin,
        json={"user_id": l2_uid, "employee_code": f"L2_{suffix.upper()}"},
    ).json()["data"]["id"]

    # Assign LECTURER role to Lecturer 2
    roles_res = client.get("/api/v1/roles", headers=headers_admin)
    lec_role_id = next(r["id"] for r in roles_res.json()["data"] if r["code"] == "LECTURER")
    client.post(
        f"/api/v1/users/{l2_uid}/role-assignments",
        headers=headers_admin,
        json={
            "role_id": lec_role_id,
            "scope_type": "UNIVERSITY",
            "scope_id": str(test_university.id),
        },
    )

    # Assign Lecturer 1 to Offering 1, Lecturer 2 to Offering 2
    client.post(
        f"/api/v1/course-offerings/{off1}/lecturers",
        headers=headers_admin,
        json={"lecturer_id": l1_id, "is_primary": True, "assignment_type": "PRIMARY"},
    )
    client.post(
        f"/api/v1/course-offerings/{off2}/lecturers",
        headers=headers_admin,
        json={"lecturer_id": l2_id, "is_primary": True, "assignment_type": "PRIMARY"},
    )

    headers_l2 = get_user_headers(client, l2_uname, l2_pwd, str(test_university.id))

    # 1. Lecturer 2 /me/offerings includes Offering 2, but NOT Offering 1
    my_offs = client.get("/api/v1/lecturers/me/offerings", headers=headers_l2)
    assert my_offs.status_code == 200
    off_ids = [o["id"] for o in my_offs.json()["data"]["items"]]
    assert off2 in off_ids
    assert off1 not in off_ids

    # 2. Lecturer 2 CANNOT manage enrollments on Offering 1 -> 403
    enr_res = client.post(
        f"/api/v1/course-offerings/{off1}/enrollments",
        headers=headers_l2,
        json={"student_id": str(uuid.uuid4())},
    )
    assert enr_res.status_code == 403

    # 3. Lecturer 2 CANNOT update Offering 1 -> 403
    patch_res = client.patch(
        f"/api/v1/course-offerings/{off1}",
        headers=headers_l2,
        json={"status": "CANCELLED"},
    )
    assert patch_res.status_code == 403


def test_revoked_rbac_assignment_loses_access(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify that revoking a role assignment immediately cuts off access
    for subsequent requests.
    """
    headers_admin = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Create Faculty
    fac_res = client.post(
        "/api/v1/academic-units",
        headers=headers_admin,
        json={"name": "Arts Faculty", "code": f"ART_{suffix}", "unit_type": "FACULTY"},
    )
    assert fac_res.status_code == 201
    fac_id = fac_res.json()["data"]["id"]

    # Create user & assign FACULTY_ADMIN on Arts Faculty
    u_id, u_name, u_pwd = create_test_user(client, headers_admin, prefix="rev_user")
    roles_res = client.get("/api/v1/roles", headers=headers_admin)
    fac_role_id = next(r["id"] for r in roles_res.json()["data"] if r["code"] == "FACULTY_ADMIN")

    assign_res = client.post(
        f"/api/v1/users/{u_id}/role-assignments",
        headers=headers_admin,
        json={"role_id": fac_role_id, "scope_type": "ACADEMIC_UNIT", "scope_id": fac_id},
    )
    assert assign_res.status_code == 201
    assignment_id = assign_res.json()["data"]["id"]

    headers_user = get_user_headers(client, u_name, u_pwd, str(test_university.id))

    # 1. User CAN create course while role is active
    c1 = client.post(
        "/api/v1/courses",
        headers=headers_user,
        json={
            "code": f"ART1_{suffix}",
            "name": "Art History",
            "academic_unit_id": fac_id,
            "credit_hours": 3,
        },
    )
    assert c1.status_code == 201

    # 2. Admin revokes the role assignment
    revoke_res = client.delete(f"/api/v1/role-assignments/{assignment_id}", headers=headers_admin)
    assert revoke_res.status_code == 200

    # 3. Same user using same access token CANNOT create course anymore -> 403
    c2 = client.post(
        "/api/v1/courses",
        headers=headers_user,
        json={
            "code": f"ART2_{suffix}",
            "name": "Sculpture",
            "academic_unit_id": fac_id,
            "credit_hours": 3,
        },
    )
    assert c2.status_code == 403
    assert c2.json()["error"]["code"] == "PERMISSION_DENIED"


def test_malicious_uuid_and_idor_attempts_rejected(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify malformed UUIDs return 422, and non-existent/IDOR UUIDs return 404 NOT_FOUND."""
    headers_admin = get_admin_headers(client, test_admin_user, test_university)

    # Malformed UUID -> 422 Unprocessable Entity
    assert client.get("/api/v1/courses/not-a-valid-uuid", headers=headers_admin).status_code == 422
    assert client.get("/api/v1/students/not-a-valid-uuid", headers=headers_admin).status_code == 422
    assert (
        client.get("/api/v1/lecturers/not-a-valid-uuid", headers=headers_admin).status_code == 422
    )
    assert client.get("/api/v1/sections/not-a-valid-uuid", headers=headers_admin).status_code == 422
    assert (
        client.get("/api/v1/course-offerings/not-a-valid-uuid", headers=headers_admin).status_code
        == 422
    )

    # Non-existent UUIDv4 -> 404 NOT_FOUND with standard error envelope
    dummy_uuid = str(uuid.uuid4())
    for endpoint in [
        f"/api/v1/courses/{dummy_uuid}",
        f"/api/v1/sections/{dummy_uuid}",
        f"/api/v1/students/{dummy_uuid}",
        f"/api/v1/lecturers/{dummy_uuid}",
        f"/api/v1/course-offerings/{dummy_uuid}",
    ]:
        res = client.get(endpoint, headers=headers_admin)
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"
