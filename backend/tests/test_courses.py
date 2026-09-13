"""Test suite for Master Course Catalog management, constraints, and isolation."""

import uuid

from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_users import get_admin_headers


def test_course_crud_and_code_uniqueness(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify course creation, code uniqueness within university,
    detail retrieval, update, and deletion.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]
    code = f"CS_{suffix}"

    # 1. Create Course
    create_res = client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "code": code,
            "name": "Database Systems",
            "credit_hours": 3,
            "description": "Relational database concepts, SQL, and indexing",
        },
    )
    assert create_res.status_code == 201
    course_data = create_res.json()["data"]
    course_id = course_data["id"]
    assert course_data["code"] == code
    assert course_data["name"] == "Database Systems"
    assert course_data["credit_hours"] == 3
    assert course_data["status"] == "ACTIVE"

    # 2. Duplicate course code rejected in same university
    dup_res = client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "code": code,
            "name": "Advanced Databases",
            "credit_hours": 4,
        },
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "CONFLICT"

    # 3. Get Course Details
    get_res = client.get(f"/api/v1/courses/{course_id}", headers=headers)
    assert get_res.status_code == 200
    detail = get_res.json()["data"]
    assert detail["id"] == course_id
    assert detail["name"] == "Database Systems"

    # 4. Update Course
    update_res = client.patch(
        f"/api/v1/courses/{course_id}",
        headers=headers,
        json={"name": "Database Management Systems", "credit_hours": 4},
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()["data"]
    assert updated_data["name"] == "Database Management Systems"
    assert updated_data["credit_hours"] == 4

    # 5. List Courses with search
    list_res = client.get(f"/api/v1/courses?search={suffix}", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["id"] == course_id

    # 6. Delete Course without offerings
    del_res = client.delete(f"/api/v1/courses/{course_id}", headers=headers)
    assert del_res.status_code == 200

    # 7. Verify deleted
    get_after_del = client.get(f"/api/v1/courses/{course_id}", headers=headers)
    assert get_after_del.status_code == 404


def test_course_university_isolation(
    client: TestClient,
    test_university: University,
    second_university: University,
    test_admin_user: User,
    second_admin_user: User,
) -> None:
    """Verify that same course code is permitted in different universities (tenant isolation)."""
    headers1 = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]
    shared_code = f"MATH_{suffix}"

    # Create in test_university
    res1 = client.post(
        "/api/v1/courses",
        headers=headers1,
        json={
            "code": shared_code,
            "name": "Linear Algebra",
            "credit_hours": 3,
        },
    )
    assert res1.status_code == 201

    # In second university, same code is allowed because of university_id scoping
    headers2 = get_admin_headers(client, second_admin_user, second_university)
    res2 = client.post(
        "/api/v1/courses",
        headers=headers2,
        json={
            "code": shared_code,
            "name": "Linear Algebra II",
            "credit_hours": 3,
        },
    )
    assert res2.status_code == 201
    assert res2.json()["data"]["code"] == shared_code
    assert res2.json()["data"]["university_id"] == str(second_university.id)


def test_create_course_with_academic_unit_validation(
    client: TestClient,
    test_university: University,
    second_university: University,
    test_admin_user: User,
) -> None:
    """Verify course creation verifies that academic unit exists in current university."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Create valid academic unit
    unit_res = client.post(
        "/api/v1/academic-units",
        headers=headers,
        json={"name": "Computer Science", "code": f"CS_DEPT_{suffix}", "unit_type": "DEPARTMENT"},
    )
    assert unit_res.status_code == 201
    unit_id = unit_res.json()["data"]["id"]

    # Valid course creation with academic unit
    course_res = client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "code": f"CS201_{suffix}",
            "name": "Data Structures",
            "academic_unit_id": unit_id,
            "credit_hours": 4,
        },
    )
    assert course_res.status_code == 201
    assert course_res.json()["data"]["academic_unit_id"] == unit_id

    # Invalid unit ID fails validation
    fake_unit_id = str(uuid.uuid4())
    bad_res = client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "code": f"CS202_{suffix}",
            "name": "Algorithms",
            "academic_unit_id": fake_unit_id,
        },
    )
    assert bad_res.status_code == 422
