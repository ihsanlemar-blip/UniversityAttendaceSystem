"""Test suite for curriculum, roster, and offering RBAC permissions and subtree scoping."""

import uuid

from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
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
