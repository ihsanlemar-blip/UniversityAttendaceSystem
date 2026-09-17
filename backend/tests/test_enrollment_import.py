"""Integration tests for Enrollment / Class Roster Data Import and Safe Commit."""

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import (
    EnrollmentStatus,
    ImportJobStatus,
    ImportRowAction,
    ImportRowStatus,
)
from backend.app.models.enrollment import Enrollment
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_people import create_test_user
from backend.tests.test_users import get_admin_headers


def create_offering_and_student(
    client: TestClient, headers: dict[str, str]
) -> tuple[str, str, str, str, str, str]:
    """Helper to create Course, Semester, Section, CourseOffering, and Student.

    Returns:
        (course_code, semester_code, section_code, student_number, offering_id, student_id)
    """
    suffix = uuid.uuid4().hex[:6].upper()
    c_code = f"CS-ENR-{suffix}"
    sem_code = f"SEM-ENR-{suffix}"
    sec_code = f"SEC-ENR-{suffix}"
    stu_number = f"STU-ENR-{suffix}"

    # 1. Course
    c_res = client.post(
        "/api/v1/courses",
        headers=headers,
        json={"code": c_code, "name": "Algorithms", "credit_hours": 3},
    )
    assert c_res.status_code == 201
    course_id = c_res.json()["data"]["id"]

    # 2. Academic Year
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

    # 3. Semester
    sem_res = client.post(
        "/api/v1/semesters",
        headers=headers,
        json={
            "academic_year_id": ay_id,
            "name": f"Semester {suffix}",
            "code": sem_code,
            "sequence_order": 1,
            "start_date": "2026-09-01",
            "end_date": "2027-01-31",
        },
    )
    assert sem_res.status_code == 201
    semester_id = sem_res.json()["data"]["id"]

    # 4. Section
    sec_res = client.post(
        "/api/v1/sections",
        headers=headers,
        json={"code": sec_code, "name": f"Section {suffix}", "semester_id": semester_id},
    )
    assert sec_res.status_code == 201
    section_id = sec_res.json()["data"]["id"]

    # 5. Course Offering
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
    offering_id = off_res.json()["data"]["id"]

    # 6. Student
    u_id, _, _ = create_test_user(client, headers, prefix=f"enr_{suffix.lower()}")
    s_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={"user_id": u_id, "student_number": stu_number},
    )
    assert s_res.status_code == 201
    student_id = s_res.json()["data"]["id"]

    return c_code, sem_code, sec_code, stu_number, offering_id, student_id


@pytest.mark.asyncio
async def test_enrollment_import_preview_non_mutation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """INVARIANT: Preview MUST NEVER mutate production enrollments table."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    c_code, sem_code, sec_code, s_num, offering_id, student_id = create_offering_and_student(
        client, headers
    )

    csv_content = (
        "student_number,course_code,semester_code,section_code,status\n"
        f"{s_num},{c_code},{sem_code},{sec_code},ACTIVE\n"
    ).encode()

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "ENROLLMENTS", "commit_mode": "STRICT"},
        files={"file": ("enrollments_preview.csv", io.BytesIO(csv_content), "text/csv")},
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

    # CRITICAL INVARIANT: Production table must NOT contain this enrollment
    e_stmt = select(Enrollment).where(
        Enrollment.university_id == test_university.id,
        Enrollment.student_id == uuid.UUID(student_id),
        Enrollment.course_offering_id == uuid.UUID(offering_id),
    )
    assert (await db_session.execute(e_stmt)).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_enrollment_import_commit_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify committing staged enrollments creates Enrollment record."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    c_code, sem_code, sec_code, s_num, offering_id, student_id = create_offering_and_student(
        client, headers
    )

    csv_content = (
        "student_number,course_code,semester_code,section_code,status\n"
        f"{s_num},{c_code},{sem_code},{sec_code},ACTIVE\n"
    ).encode()

    # 1. Preview
    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "ENROLLMENTS", "commit_mode": "STRICT"},
        files={"file": ("enrollments.csv", io.BytesIO(csv_content), "text/csv")},
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
    e_stmt = select(Enrollment).where(
        Enrollment.university_id == test_university.id,
        Enrollment.student_id == uuid.UUID(student_id),
        Enrollment.course_offering_id == uuid.UUID(offering_id),
    )
    enrollment = (await db_session.execute(e_stmt)).scalar_one_or_none()
    assert enrollment is not None
    assert enrollment.status == EnrollmentStatus.ACTIVE.value

    # Double commit rejected
    double_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=headers, json={})
    assert double_res.status_code == 409


@pytest.mark.asyncio
async def test_enrollment_import_missing_entities_errors(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify non-existent student, course, semester, section codes trigger row errors."""
    headers = get_admin_headers(client, test_admin_user, test_university)

    csv_content = (
        b"student_number,course_code,semester_code,section_code\n"
        b"STU-NONEXISTENT,CS-NONEXISTENT,SEM-NONEXISTENT,SEC-NONEXISTENT\n"
    )

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "ENROLLMENTS", "commit_mode": "STRICT"},
        files={"file": ("bad_enr.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201
    job = res.json()["data"]["job"]
    assert job["error_count"] == 1

    job_id = job["id"]
    rows_res = client.get(f"/api/v1/imports/{job_id}/rows", headers=headers)
    rows = rows_res.json()["data"]["items"]

    error_codes = [e["code"] for e in rows[0]["errors"]]
    assert "STUDENT_NOT_FOUND" in error_codes
    assert "COURSE_NOT_FOUND" in error_codes
    assert "SEMESTER_NOT_FOUND" in error_codes

    # Strict mode commit rejected
    commit_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=headers, json={})
    assert commit_res.status_code == 422


@pytest.mark.asyncio
async def test_enrollment_import_update_existing_and_intra_file_duplicate(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify updating existing enrollment status to DROPPED and intra-file dup detection."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    c_code, sem_code, sec_code, s_num, offering_id, student_id = create_offering_and_student(
        client, headers
    )

    # First import: create ACTIVE enrollment
    csv_v1 = (
        "student_number,course_code,semester_code,section_code,status\n"
        f"{s_num},{c_code},{sem_code},{sec_code},ACTIVE\n"
    ).encode()
    res1 = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "ENROLLMENTS"},
        files={"file": ("v1.csv", io.BytesIO(csv_v1), "text/csv")},
    )
    assert res1.status_code == 201
    job1_id = res1.json()["data"]["job"]["id"]
    client.post(f"/api/v1/imports/{job1_id}/commit", headers=headers, json={})

    # Second import: update to DROPPED, plus an intra-file duplicate row
    csv_v2 = (
        "student_number,course_code,semester_code,section_code,status\n"
        f"{s_num},{c_code},{sem_code},{sec_code},DROPPED\n"
        f"{s_num},{c_code},{sem_code},{sec_code},ACTIVE\n"
    ).encode()

    res2 = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "ENROLLMENTS", "commit_mode": "PARTIAL"},
        files={"file": ("v2.csv", io.BytesIO(csv_v2), "text/csv")},
    )
    assert res2.status_code == 201
    job2_id = res2.json()["data"]["job"]["id"]

    rows_res = client.get(f"/api/v1/imports/{job2_id}/rows", headers=headers)
    rows = rows_res.json()["data"]["items"]

    # Row 0 is UPDATE with WARNING
    assert rows[0]["action"] == ImportRowAction.UPDATE.value
    assert rows[0]["status"] == ImportRowStatus.WARNING.value

    # Row 1 is DUPLICATE_IN_FILE with ERROR
    assert rows[1]["status"] == ImportRowStatus.ERROR.value
    assert rows[1]["errors"][0]["code"] == "DUPLICATE_IN_FILE"

    # Commit PARTIAL mode: Row 0 commits, Row 1 skipped
    commit_res = client.post(f"/api/v1/imports/{job2_id}/commit", headers=headers, json={})
    assert commit_res.status_code == 200
    commit_data = commit_res.json()["data"]
    assert commit_data["commit_count"] == 1
    assert commit_data["summary"]["skipped_count"] == 1

    # Verify in DB: enrollment status changed to DROPPED
    e_stmt = select(Enrollment).where(
        Enrollment.university_id == test_university.id,
        Enrollment.student_id == uuid.UUID(student_id),
        Enrollment.course_offering_id == uuid.UUID(offering_id),
    )
    enrollment = (await db_session.execute(e_stmt)).scalar_one()
    assert enrollment.status == EnrollmentStatus.DROPPED.value
