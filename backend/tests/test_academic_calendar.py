"""Test suite for academic calendar, year and semester lifecycle, and intervals."""

import uuid

from fastapi.testclient import TestClient

from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_users import get_admin_headers


def test_academic_year_lifecycle_and_validation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify academic year creation, date bounds validation, and code uniqueness."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # 1. Invalid date range: start_date >= end_date
    bad_res = client.post(
        "/api/v1/academic-years",
        headers=headers,
        json={
            "name": "Invalid Year",
            "code": f"BAD_{suffix}",
            "start_date": "2026-09-01",
            "end_date": "2026-05-01",  # before start_date
        },
    )
    assert bad_res.status_code in (400, 422)

    # 2. Valid creation
    code = f"AY_{suffix}"
    res = client.post(
        "/api/v1/academic-years",
        headers=headers,
        json={
            "name": "Academic Year 2026-2027",
            "code": code,
            "start_date": "2026-09-01",
            "end_date": "2027-06-30",
            "is_current": True,
        },
    )
    assert res.status_code == 201
    year_data = res.json()["data"]
    assert year_data["is_current"] is True

    # 3. Duplicate code rejected
    dup_res = client.post(
        "/api/v1/academic-years",
        headers=headers,
        json={
            "name": "Duplicate Year",
            "code": code,
            "start_date": "2026-09-01",
            "end_date": "2027-06-30",
        },
    )
    assert dup_res.status_code == 409


def test_single_active_academic_year_exclusivity(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Only one academic year may have is_current=True at a time per university."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Create Year 1 as current
    y1_res = client.post(
        "/api/v1/academic-years",
        headers=headers,
        json={
            "name": "Year 1",
            "code": f"Y1_{suffix}",
            "start_date": "2024-09-01",
            "end_date": "2025-06-30",
            "is_current": True,
        },
    )
    y1_id = y1_res.json()["data"]["id"]

    # Create Year 2 as current
    y2_res = client.post(
        "/api/v1/academic-years",
        headers=headers,
        json={
            "name": "Year 2",
            "code": f"Y2_{suffix}",
            "start_date": "2025-09-01",
            "end_date": "2026-06-30",
            "is_current": True,
        },
    )
    y2_id = y2_res.json()["data"]["id"]

    # Verify Year 1 was automatically deactivated
    y1_check = client.get(f"/api/v1/academic-years/{y1_id}", headers=headers)
    assert y1_check.json()["data"]["is_current"] is False

    # Verify /current endpoint returns Year 2
    cur_res = client.get("/api/v1/academic-years/current", headers=headers)
    assert cur_res.status_code == 200
    assert cur_res.json()["data"]["id"] == y2_id

    # Switch back to Year 1 via set-current endpoint
    switch_res = client.post(f"/api/v1/academic-years/{y1_id}/set-current", headers=headers)
    assert switch_res.status_code == 200
    assert switch_res.json()["data"]["is_current"] is True

    # Year 2 should now be False
    y2_check = client.get(f"/api/v1/academic-years/{y2_id}", headers=headers)
    assert y2_check.json()["data"]["is_current"] is False


def test_semester_enclosure_and_lifecycle(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify semester date containment within parent academic year bounds."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    suffix = uuid.uuid4().hex[:6]

    # Create parent academic year: Sep 1, 2026 to Jun 30, 2027
    year_res = client.post(
        "/api/v1/academic-years",
        headers=headers,
        json={
            "name": "Calendar Bounds Year",
            "code": f"CBY_{suffix}",
            "start_date": "2026-09-01",
            "end_date": "2027-06-30",
        },
    )
    year_id = year_res.json()["data"]["id"]

    # 1. Semester start before parent year start -> rejected
    bad_start_res = client.post(
        "/api/v1/semesters",
        headers=headers,
        json={
            "academic_year_id": year_id,
            "name": "Early Semester",
            "code": f"EARLY_{suffix}",
            "start_date": "2026-08-15",  # before year start
            "end_date": "2027-01-15",
        },
    )
    assert bad_start_res.status_code == 422

    # 2. Semester end after parent year end -> rejected
    bad_end_res = client.post(
        "/api/v1/semesters",
        headers=headers,
        json={
            "academic_year_id": year_id,
            "name": "Late Semester",
            "code": f"LATE_{suffix}",
            "start_date": "2027-02-01",
            "end_date": "2027-07-15",  # after year end
        },
    )
    assert bad_end_res.status_code == 422

    # 3. Valid Fall Semester
    sem1_res = client.post(
        "/api/v1/semesters",
        headers=headers,
        json={
            "academic_year_id": year_id,
            "name": "Fall Semester 2026",
            "code": f"FALL_{suffix}",
            "sequence_order": 1,
            "start_date": "2026-09-05",
            "end_date": "2027-01-20",
            "is_current": True,
        },
    )
    assert sem1_res.status_code == 201
    sem1_data = sem1_res.json()["data"]
    assert sem1_data["is_current"] is True

    # 4. Valid Spring Semester
    sem2_res = client.post(
        "/api/v1/semesters",
        headers=headers,
        json={
            "academic_year_id": year_id,
            "name": "Spring Semester 2027",
            "code": f"SPRING_{suffix}",
            "sequence_order": 2,
            "start_date": "2027-02-01",
            "end_date": "2027-06-25",
            "is_current": True,
        },
    )
    assert sem2_res.status_code == 201
    sem2_data = sem2_res.json()["data"]
    assert sem2_data["is_current"] is True

    # Verify sem1 is now is_current=False
    sem1_check = client.get(f"/api/v1/semesters/{sem1_data['id']}", headers=headers)
    assert sem1_check.json()["data"]["is_current"] is False

    # 5. Verify Year detail embeds both semesters in order
    year_detail = client.get(f"/api/v1/academic-years/{year_id}", headers=headers)
    assert year_detail.status_code == 200
    sems = year_detail.json()["data"]["semesters"]
    assert len(sems) == 2
    assert sems[0]["sequence_order"] == 1
    assert sems[1]["sequence_order"] == 2
