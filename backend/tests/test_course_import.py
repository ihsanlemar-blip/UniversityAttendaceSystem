"""Integration tests for Course Catalog Data Import, Validation, Preview, and Safe Commit."""

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
    RecordStatus,
)
from backend.app.models.course import Course
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_course_import_preview_non_mutation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """INVARIANT: Preview MUST NEVER mutate production courses table."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6].upper()
    course_code = f"CS-PREV-{prefix}"

    csv_content = (
        "code,name,credit_hours,description\n"
        f"{course_code},سیستم‌های عامل,4,Operating Systems foundational principles\n"
    ).encode()

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "COURSES", "commit_mode": "STRICT"},
        files={"file": ("courses_preview.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201, res.text
    body = res.json()["data"]
    job_id = body["job"]["id"]

    assert body["job"]["row_count"] == 1
    assert body["job"]["valid_count"] == 1
    assert body["job"]["error_count"] == 0
    assert body["job"]["status"] == ImportJobStatus.READY.value

    # Verify staging row
    rows_res = client.get(f"/api/v1/imports/{job_id}/rows", headers=headers)
    assert rows_res.status_code == 200
    rows_data = rows_res.json()["data"]["items"]
    assert len(rows_data) == 1
    assert rows_data[0]["status"] == ImportRowStatus.VALID.value
    assert rows_data[0]["action"] == ImportRowAction.CREATE.value

    # CRITICAL INVARIANT: Production table must NOT contain this course
    c_stmt = select(Course).where(
        Course.university_id == test_university.id,
        Course.code == course_code,
    )
    assert (await db_session.execute(c_stmt)).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_course_import_commit_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify committing staged courses creates Course record."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6].upper()
    course_code = f"CS-COM-{prefix}"

    csv_content = (
        "code,name,credit_hours,description,status\n"
        f"{course_code},الگوریتم‌های پیشرفته,3,Advanced Algorithms,ACTIVE\n"
    ).encode()

    # 1. Preview
    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "COURSES", "commit_mode": "STRICT"},
        files={"file": ("courses.csv", io.BytesIO(csv_content), "text/csv")},
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
    c_stmt = select(Course).where(
        Course.university_id == test_university.id,
        Course.code == course_code,
    )
    course = (await db_session.execute(c_stmt)).scalar_one_or_none()
    assert course is not None
    assert course.name == "الگوریتم‌های پیشرفته"
    assert course.credit_hours == 3
    assert course.status == RecordStatus.ACTIVE.value

    # Double commit rejected
    double_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=headers, json={})
    assert double_res.status_code == 409


@pytest.mark.asyncio
async def test_course_import_update_existing_course(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify importing an existing course updates name and credit hours."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6].upper()
    course_code = f"CS-UPD-{prefix}"

    # First import: create
    csv_v1 = (
        f"code,name,credit_hours,status\n{course_code},Software Engineering I,3,ACTIVE\n"
    ).encode()

    res1 = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "COURSES"},
        files={"file": ("v1.csv", io.BytesIO(csv_v1), "text/csv")},
    )
    assert res1.status_code == 201
    job1_id = res1.json()["data"]["job"]["id"]
    client.post(f"/api/v1/imports/{job1_id}/commit", headers=headers, json={})

    # Second import: update
    csv_v2 = (
        f"code,name,credit_hours,status\n{course_code},مهندسی نرم‌افزار پیشرفته,4,ACTIVE\n"
    ).encode()

    res2 = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "COURSES"},
        files={"file": ("v2.csv", io.BytesIO(csv_v2), "text/csv")},
    )
    assert res2.status_code == 201
    job2_id = res2.json()["data"]["job"]["id"]

    rows_res = client.get(f"/api/v1/imports/{job2_id}/rows", headers=headers)
    rows = rows_res.json()["data"]["items"]
    assert rows[0]["action"] == ImportRowAction.UPDATE.value
    assert rows[0]["status"] == ImportRowStatus.WARNING.value

    # Commit update
    commit_res = client.post(f"/api/v1/imports/{job2_id}/commit", headers=headers, json={})
    assert commit_res.status_code == 200

    # Verify database update
    c_stmt = select(Course).where(
        Course.university_id == test_university.id,
        Course.code == course_code,
    )
    updated_course = (await db_session.execute(c_stmt)).scalar_one()
    assert updated_course.name == "مهندسی نرم‌افزار پیشرفته"
    assert updated_course.credit_hours == 4


@pytest.mark.asyncio
async def test_course_import_invalid_credits_and_unit(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify out-of-range credits and invalid academic units trigger errors."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6].upper()

    csv_content = (
        "code,name,credit_hours,academic_unit_code\n"
        f"BAD-CR-{prefix},Bad Credits,999,CS\n"
        f"BAD-UN-{prefix},Bad Unit,3,NON_EXISTENT_FACULTY_XYZ\n"
    ).encode()

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "COURSES", "commit_mode": "STRICT"},
        files={"file": ("bad_courses.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201
    job = res.json()["data"]["job"]
    assert job["error_count"] == 2

    job_id = job["id"]
    rows_res = client.get(f"/api/v1/imports/{job_id}/rows", headers=headers)
    rows = rows_res.json()["data"]["items"]

    r0_codes = [e["code"] for e in rows[0]["errors"]]
    assert "INVALID_CREDIT_HOURS" in r0_codes

    r1_codes = [e["code"] for e in rows[1]["errors"]]
    assert "ACADEMIC_UNIT_NOT_FOUND" in r1_codes

    # Strict mode commit rejected
    commit_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=headers, json={})
    assert commit_res.status_code == 422


@pytest.mark.asyncio
async def test_course_import_intra_file_duplicate(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify intra-file duplicate course code triggers row error."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6].upper()
    dup_code = f"CS-DUP-{prefix}"

    csv_content = (
        f"code,name,credit_hours\n{dup_code},Intro to Database,3\n{dup_code},Duplicate Course,3\n"
    ).encode()

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "COURSES", "commit_mode": "STRICT"},
        files={"file": ("dup_courses.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201
    job = res.json()["data"]["job"]
    assert job["error_count"] == 1

    job_id = job["id"]
    rows_res = client.get(f"/api/v1/imports/{job_id}/rows", headers=headers)
    rows = rows_res.json()["data"]["items"]
    assert rows[1]["errors"][0]["code"] == "DUPLICATE_IN_FILE"
