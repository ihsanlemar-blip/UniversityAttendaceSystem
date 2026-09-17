"""Integration tests for Course Offering Data Import, Validation, Preview, and Safe Commit."""

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
    OfferingStatus,
)
from backend.app.models.course_offering import CourseOffering
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_offerings import setup_academic_prerequisites
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_offering_import_preview_non_mutation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """INVARIANT: Preview MUST NEVER mutate production course offerings table."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers)

    # Fetch course and semester codes
    c_res = client.get(f"/api/v1/courses/{course_id}", headers=headers)
    course_code = c_res.json()["data"]["code"]
    sem_res = client.get(f"/api/v1/semesters/{semester_id}", headers=headers)
    sem_code = sem_res.json()["data"]["code"]
    sec_res = client.get(f"/api/v1/sections/{section_id}", headers=headers)
    sec_code = sec_res.json()["data"]["code"]

    csv_content = (
        "course_code,semester_code,section_code,status\n"
        f"{course_code},{sem_code},{sec_code},ACTIVE\n"
    ).encode()

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "COURSE_OFFERINGS", "commit_mode": "STRICT"},
        files={"file": ("offerings_preview.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201, res.text
    body = res.json()["data"]
    job_id = body["job"]["id"]

    assert body["job"]["row_count"] == 1
    assert body["job"]["valid_count"] == 1
    assert body["job"]["error_count"] == 0
    assert body["job"]["status"] == ImportJobStatus.READY.value

    # Verify staging rows
    rows_res = client.get(f"/api/v1/imports/{job_id}/rows", headers=headers)
    assert rows_res.status_code == 200
    rows_data = rows_res.json()["data"]["items"]
    assert len(rows_data) == 1
    assert rows_data[0]["status"] == ImportRowStatus.VALID.value
    assert rows_data[0]["action"] == ImportRowAction.CREATE.value

    # CRITICAL INVARIANT: Production table must NOT contain this offering
    off_stmt = select(CourseOffering).where(
        CourseOffering.university_id == test_university.id,
        CourseOffering.course_id == uuid.UUID(course_id),
        CourseOffering.semester_id == uuid.UUID(semester_id),
    )
    assert (await db_session.execute(off_stmt)).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_offering_import_commit_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify committing staged course offerings creates CourseOffering record."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, headers)

    c_res = client.get(f"/api/v1/courses/{course_id}", headers=headers)
    course_code = c_res.json()["data"]["code"]
    sem_res = client.get(f"/api/v1/semesters/{semester_id}", headers=headers)
    sem_code = sem_res.json()["data"]["code"]
    sec_res = client.get(f"/api/v1/sections/{section_id}", headers=headers)
    sec_code = sec_res.json()["data"]["code"]

    csv_content = (
        "course_code,semester_code,section_code,status\n"
        f"{course_code},{sem_code},{sec_code},ACTIVE\n"
    ).encode()

    # 1. Preview
    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "COURSE_OFFERINGS", "commit_mode": "STRICT"},
        files={"file": ("offerings.csv", io.BytesIO(csv_content), "text/csv")},
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
    off_stmt = select(CourseOffering).where(
        CourseOffering.university_id == test_university.id,
        CourseOffering.course_id == uuid.UUID(course_id),
        CourseOffering.semester_id == uuid.UUID(semester_id),
    )
    offering = (await db_session.execute(off_stmt)).scalar_one_or_none()
    assert offering is not None
    assert offering.status == OfferingStatus.ACTIVE.value
    assert offering.section_id == uuid.UUID(section_id)

    # Double commit rejected
    double_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=headers, json={})
    assert double_res.status_code == 409


@pytest.mark.asyncio
async def test_offering_import_errors_and_intra_file_duplicate(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify non-existent course/semester and intra-file dupes trigger row errors."""
    headers = get_admin_headers(client, test_admin_user, test_university)

    csv_content = (
        b"course_code,semester_code,section_code\n"
        b"CS-NONEXISTENT,SEM-NONEXISTENT,SEC-A\n"
        b"CS-NONEXISTENT,SEM-NONEXISTENT,SEC-A\n"
    )

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "COURSE_OFFERINGS", "commit_mode": "STRICT"},
        files={"file": ("bad_off.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201
    job = res.json()["data"]["job"]
    assert job["error_count"] == 2

    job_id = job["id"]
    rows_res = client.get(f"/api/v1/imports/{job_id}/rows", headers=headers)
    rows = rows_res.json()["data"]["items"]

    # Row 0 has COURSE_NOT_FOUND and SEMESTER_NOT_FOUND
    r0_codes = [e["code"] for e in rows[0]["errors"]]
    assert "COURSE_NOT_FOUND" in r0_codes
    assert "SEMESTER_NOT_FOUND" in r0_codes

    # Row 1 has DUPLICATE_IN_FILE
    r1_codes = [e["code"] for e in rows[1]["errors"]]
    assert "DUPLICATE_IN_FILE" in r1_codes
