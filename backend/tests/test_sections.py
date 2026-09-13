"""Test suite for Section cohorts and semester associations."""

import uuid

from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_users import get_admin_headers


def test_section_crud_and_uniqueness(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify section cohort creation, semester uniqueness, and update."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Create an academic year and semester
    ay_res = client.post(
        "/api/v1/academic-years",
        headers=headers,
        json={
            "name": f"Academic Year {suffix}",
            "code": f"AY_{suffix}",
            "start_date": "2026-09-01",
            "end_date": "2027-06-30",
        },
    )
    assert ay_res.status_code == 201
    ay_id = ay_res.json()["data"]["id"]

    sem_res = client.post(
        "/api/v1/semesters",
        headers=headers,
        json={
            "academic_year_id": ay_id,
            "name": "Fall 2026",
            "code": f"FALL_{suffix}",
            "sequence_order": 1,
            "start_date": "2026-09-01",
            "end_date": "2027-01-31",
        },
    )
    assert sem_res.status_code == 201
    sem_id = sem_res.json()["data"]["id"]

    # 1. Create Section
    sec_res = client.post(
        "/api/v1/sections",
        headers=headers,
        json={
            "code": "A",
            "name": "Section A Morning",
            "semester_id": sem_id,
        },
    )
    assert sec_res.status_code == 201
    sec_data = sec_res.json()["data"]
    sec_id = sec_data["id"]
    assert sec_data["code"] == "A"
    assert sec_data["semester_id"] == sem_id

    # 2. Duplicate section code in same semester rejected
    dup_res = client.post(
        "/api/v1/sections",
        headers=headers,
        json={
            "code": "A",
            "name": "Another Section A",
            "semester_id": sem_id,
        },
    )
    assert dup_res.status_code == 409

    # 3. Same section code in another semester allowed
    sem2_res = client.post(
        "/api/v1/semesters",
        headers=headers,
        json={
            "academic_year_id": ay_id,
            "name": "Spring 2027",
            "code": f"SPRING_{suffix}",
            "sequence_order": 2,
            "start_date": "2027-02-01",
            "end_date": "2027-06-30",
        },
    )
    assert sem2_res.status_code == 201
    sem2_id = sem2_res.json()["data"]["id"]

    sec2_res = client.post(
        "/api/v1/sections",
        headers=headers,
        json={
            "code": "A",
            "name": "Spring Section A",
            "semester_id": sem2_id,
        },
    )
    assert sec2_res.status_code == 201
    assert sec2_res.json()["data"]["semester_id"] == sem2_id

    # 4. Get section detail
    get_res = client.get(f"/api/v1/sections/{sec_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["name"] == "Section A Morning"
    assert get_res.json()["data"]["semester_name"] == "Fall 2026"

    # 5. Update section
    upd_res = client.patch(
        f"/api/v1/sections/{sec_id}",
        headers=headers,
        json={"name": "Section A Prime Morning"},
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["data"]["name"] == "Section A Prime Morning"

    # 6. List sections by semester
    list_res = client.get(f"/api/v1/sections?semester_id={sem_id}", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["id"] == sec_id
