"""Test suite for Student and Lecturer profile management, constraints, and isolation."""

import uuid

from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_users import get_admin_headers


def get_user_headers(
    client: TestClient, username: str, password: str, university_id: str
) -> dict[str, str]:
    """Helper to log in a user and return authorization headers."""
    res = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": password,
            "university_id": university_id,
        },
    )
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["data"]["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_test_user(
    client: TestClient, headers: dict[str, str], prefix: str = "usr"
) -> tuple[str, str, str]:
    """Helper to create a user and return (user_id, username, password)."""
    suffix = uuid.uuid4().hex[:6]
    username = f"{prefix}_{suffix}"
    password = "UserPassword123!"
    res = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": username,
            "password": password,
            "email": f"{username}@test.edu",
        },
    )
    assert res.status_code == 201
    return res.json()["data"]["id"], username, password


def test_student_profile_crud_and_uniqueness(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify student profile creation, student_number uniqueness, user 1:1,
    detail, update, and /me.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    user_id, username, password = create_test_user(client, headers, prefix="stu")
    student_num = f"STU_{uuid.uuid4().hex[:6].upper()}"

    # 1. Create Student Profile
    create_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={
            "user_id": user_id,
            "student_number": student_num,
            "admission_date": "2024-09-01",
        },
    )
    assert create_res.status_code == 201
    stu_data = create_res.json()["data"]
    stu_id = stu_data["id"]
    assert stu_data["student_number"] == student_num
    assert stu_data["status"] == "ACTIVE"
    assert stu_data["user_id"] == user_id

    # 2. Duplicate student_number rejected with CONFLICT
    user2_id, _, _ = create_test_user(client, headers, prefix="stu2")
    dup_num_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={
            "user_id": user2_id,
            "student_number": student_num,
        },
    )
    assert dup_num_res.status_code == 409
    assert dup_num_res.json()["error"]["code"] == "CONFLICT"

    # 3. Duplicate user_id (1:1 constraint) rejected with CONFLICT
    dup_user_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={
            "user_id": user_id,
            "student_number": f"DIFF_{uuid.uuid4().hex[:6].upper()}",
        },
    )
    assert dup_user_res.status_code == 409
    assert dup_user_res.json()["error"]["code"] == "CONFLICT"

    # 4. Get Student by ID
    get_res = client.get(f"/api/v1/students/{stu_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == stu_id
    assert get_res.json()["data"]["username"] == username

    # 5. Update Student profile
    update_res = client.patch(
        f"/api/v1/students/{stu_id}",
        headers=headers,
        json={
            "status": "SUSPENDED",
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["status"] == "SUSPENDED"

    # 6. Verify /students/me for this student's user
    stu_headers = get_user_headers(client, username, password, str(test_university.id))
    me_res = client.get("/api/v1/students/me", headers=stu_headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["id"] == stu_id
    assert me_res.json()["data"]["student_number"] == student_num

    # Admin user calling /students/me returns 404 (not a student)
    admin_me_res = client.get("/api/v1/students/me", headers=headers)
    assert admin_me_res.status_code == 404


def test_lecturer_profile_crud_and_uniqueness(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify lecturer profile creation, employee_code uniqueness, user 1:1,
    detail, update, and /me.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    user_id, username, password = create_test_user(client, headers, prefix="lec")
    employee_code = f"EMP_{uuid.uuid4().hex[:6].upper()}"

    # 1. Create Lecturer Profile
    create_res = client.post(
        "/api/v1/lecturers",
        headers=headers,
        json={
            "user_id": user_id,
            "employee_code": employee_code,
            "title": "Dr.",
        },
    )
    assert create_res.status_code == 201
    lec_data = create_res.json()["data"]
    lec_id = lec_data["id"]
    assert lec_data["employee_code"] == employee_code
    assert lec_data["title"] == "Dr."
    assert lec_data["status"] == "ACTIVE"
    assert lec_data["user_id"] == user_id

    # 2. Duplicate employee_code rejected with CONFLICT
    user2_id, _, _ = create_test_user(client, headers, prefix="lec2")
    dup_code_res = client.post(
        "/api/v1/lecturers",
        headers=headers,
        json={
            "user_id": user2_id,
            "employee_code": employee_code,
        },
    )
    assert dup_code_res.status_code == 409
    assert dup_code_res.json()["error"]["code"] == "CONFLICT"

    # 3. Duplicate user_id (1:1 constraint) rejected with CONFLICT
    dup_user_res = client.post(
        "/api/v1/lecturers",
        headers=headers,
        json={
            "user_id": user_id,
            "employee_code": f"DIFF_{uuid.uuid4().hex[:6].upper()}",
        },
    )
    assert dup_user_res.status_code == 409
    assert dup_user_res.json()["error"]["code"] == "CONFLICT"

    # 4. Get Lecturer by ID
    get_res = client.get(f"/api/v1/lecturers/{lec_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == lec_id
    assert get_res.json()["data"]["username"] == username

    # 5. Update Lecturer
    update_res = client.patch(
        f"/api/v1/lecturers/{lec_id}",
        headers=headers,
        json={
            "title": "Professor",
            "status": "ON_LEAVE",
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["title"] == "Professor"
    assert update_res.json()["data"]["status"] == "ON_LEAVE"

    # 6. Verify /lecturers/me
    lec_headers = get_user_headers(client, username, password, str(test_university.id))
    me_res = client.get("/api/v1/lecturers/me", headers=lec_headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["id"] == lec_id
    assert me_res.json()["data"]["employee_code"] == employee_code

    # Admin user calling /lecturers/me returns 404
    admin_me_res = client.get("/api/v1/lecturers/me", headers=headers)
    assert admin_me_res.status_code == 404


def test_people_cross_tenant_isolation(
    client: TestClient,
    test_university: University,
    second_university: University,
    test_admin_user: User,
    second_admin_user: User,
) -> None:
    """Verify that student numbers and employee codes can collide across different universities."""
    headers1 = get_admin_headers(client, test_admin_user, test_university)
    headers2 = get_admin_headers(client, second_admin_user, second_university)

    shared_stu_num = f"ISO_STU_{uuid.uuid4().hex[:6].upper()}"
    shared_emp_code = f"ISO_EMP_{uuid.uuid4().hex[:6].upper()}"

    # University 1 creates student and lecturer
    u1_stu, _, _ = create_test_user(client, headers1, prefix="u1_s")
    u1_lec, _, _ = create_test_user(client, headers1, prefix="u1_l")

    res_stu1 = client.post(
        "/api/v1/students",
        headers=headers1,
        json={
            "user_id": u1_stu,
            "student_number": shared_stu_num,
        },
    )
    assert res_stu1.status_code == 201

    res_lec1 = client.post(
        "/api/v1/lecturers",
        headers=headers1,
        json={
            "user_id": u1_lec,
            "employee_code": shared_emp_code,
        },
    )
    assert res_lec1.status_code == 201

    # University 2 creates student and lecturer with identical codes
    u2_stu, _, _ = create_test_user(client, headers2, prefix="u2_s")
    u2_lec, _, _ = create_test_user(client, headers2, prefix="u2_l")

    res_stu2 = client.post(
        "/api/v1/students",
        headers=headers2,
        json={
            "user_id": u2_stu,
            "student_number": shared_stu_num,
        },
    )
    assert res_stu2.status_code == 201
    assert res_stu2.json()["data"]["student_number"] == shared_stu_num
    assert res_stu2.json()["data"]["university_id"] == str(second_university.id)

    res_lec2 = client.post(
        "/api/v1/lecturers",
        headers=headers2,
        json={
            "user_id": u2_lec,
            "employee_code": shared_emp_code,
        },
    )
    assert res_lec2.status_code == 201
    assert res_lec2.json()["data"]["employee_code"] == shared_emp_code
    assert res_lec2.json()["data"]["university_id"] == str(second_university.id)
