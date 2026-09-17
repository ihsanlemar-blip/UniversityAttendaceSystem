"""Integration tests for Student Data Import, Validation, Preview, and Safe Commit."""

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import (
    ImportJobStatus,
    ImportRowStatus,
)
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.student import Student
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_student_import_preview_non_mutation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """INVARIANT: Preview MUST NEVER mutate production domain tables (students, users)."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]
    snum = f"STU-PREV-{prefix}"

    csv_content = (
        f"student_number,first_name,last_name,email\n{snum},احمد,محمدی,prev_{prefix}@kabul.edu.af\n"
    ).encode()

    # Upload preview
    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "STUDENTS", "commit_mode": "STRICT"},
        files={"file": ("students_preview.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201, res.text
    body = res.json()["data"]
    job_id = body["job"]["id"]

    assert body["job"]["row_count"] == 1
    assert body["job"]["valid_count"] == 1
    assert body["job"]["error_count"] == 0
    assert body["job"]["status"] == ImportJobStatus.READY.value

    # Verify staging rows were created
    rows_res = client.get(f"/api/v1/imports/{job_id}/rows", headers=headers)
    assert rows_res.status_code == 200
    rows_data = rows_res.json()["data"]["items"]
    assert len(rows_data) == 1
    assert rows_data[0]["status"] == ImportRowStatus.VALID.value

    # CRITICAL INVARIANT: Production tables must NOT contain this student or user yet!
    s_stmt = select(Student).where(
        Student.university_id == test_university.id,
        Student.student_number == snum,
    )
    assert (await db_session.execute(s_stmt)).scalar_one_or_none() is None

    u_stmt = select(User).where(
        User.university_id == test_university.id,
        User.username == snum.lower().replace("-", "_"),
    )
    assert (await db_session.execute(u_stmt)).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_student_import_commit_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify committing staged students creates User, assigns Role, and creates Student."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]
    snum = f"STU-COMMIT-{prefix}"
    expected_username = snum.lower().replace("-", "_")

    csv_content = (
        "student_number,first_name,last_name,email,phone,admission_date\n"
        f"{snum},احمد,محمدی,commit_{prefix}@kabul.edu.af,+93700112233,2026-03-21\n"
    ).encode()

    # 1. Preview
    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "STUDENTS", "commit_mode": "STRICT"},
        files={"file": ("students.csv", io.BytesIO(csv_content), "text/csv")},
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
    s_stmt = select(Student).where(
        Student.university_id == test_university.id,
        Student.student_number == snum,
    )
    student = (await db_session.execute(s_stmt)).scalar_one_or_none()
    assert student is not None
    assert str(student.admission_date) == "2026-03-21"

    user = await db_session.get(User, student.user_id)
    assert user is not None
    assert user.username == expected_username
    assert user.email == f"commit_{prefix}@kabul.edu.af"
    assert user.phone == "+93700112233"
    assert user.must_change_password is True

    # Verify role assignment
    ra_stmt = select(RoleAssignment).where(
        RoleAssignment.user_id == user.id,
        RoleAssignment.university_id == test_university.id,
    )
    assignments = list((await db_session.execute(ra_stmt)).scalars().all())
    assert len(assignments) >= 1

    # Verify double commit is rejected
    double_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=headers, json={})
    assert double_res.status_code == 409


@pytest.mark.asyncio
async def test_student_import_intra_file_duplicate_and_unknown_unit(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify intra-file duplicate student numbers and missing units produce row errors."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]
    dup_snum = f"STU-DUP-{prefix}"

    csv_content = (
        "student_number,first_name,last_name,academic_unit_code\n"
        f"{dup_snum},First,One,NON_EXISTENT_UNIT\n"
        f"{dup_snum},First,Two,NON_EXISTENT_UNIT\n"
    ).encode()

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "STUDENTS", "commit_mode": "STRICT"},
        files={"file": ("dup_students.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201
    job = res.json()["data"]["job"]
    assert job["row_count"] == 2
    assert job["error_count"] >= 1

    job_id = job["id"]
    rows_res = client.get(f"/api/v1/imports/{job_id}/rows", headers=headers)
    rows = rows_res.json()["data"]["items"]

    # Row 1 has ACADEMIC_UNIT_NOT_FOUND
    r1_error_codes = [e["code"] for e in rows[0]["errors"]]
    assert "ACADEMIC_UNIT_NOT_FOUND" in r1_error_codes

    # Row 2 has DUPLICATE_IN_FILE
    r2_error_codes = [e["code"] for e in rows[1]["errors"]]
    assert "DUPLICATE_IN_FILE" in r2_error_codes

    # STRICT mode commit must fail
    commit_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=headers, json={})
    assert commit_res.status_code == 422


@pytest.mark.asyncio
async def test_student_import_partial_mode_commit(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify PARTIAL commit mode commits valid rows and skips error rows."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]
    valid_snum = f"STU-VALID-{prefix}"
    invalid_snum = f"STU-BAD-{prefix}"

    csv_content = (
        "student_number,first_name,last_name,academic_unit_code\n"
        f"{valid_snum},Valid,Student,\n"
        f"{invalid_snum},Invalid,Student,DOES_NOT_EXIST_UNIT\n"
    ).encode()

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "STUDENTS", "commit_mode": "PARTIAL"},
        files={"file": ("partial_students.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201
    job_id = res.json()["data"]["job"]["id"]

    commit_res = client.post(
        f"/api/v1/imports/{job_id}/commit",
        headers=headers,
        json={"commit_mode": "PARTIAL"},
    )
    assert commit_res.status_code == 200
    data = commit_res.json()["data"]
    assert data["commit_count"] == 1
    assert data["summary"]["skipped_count"] == 1

    # Valid student committed
    s_stmt = select(Student).where(
        Student.university_id == test_university.id,
        Student.student_number == valid_snum,
    )
    assert (await db_session.execute(s_stmt)).scalar_one_or_none() is not None

    # Invalid student skipped
    bad_stmt = select(Student).where(
        Student.university_id == test_university.id,
        Student.student_number == invalid_snum,
    )
    assert (await db_session.execute(bad_stmt)).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_student_import_database_duplicate_updates(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify re-importing an existing student triggers UPDATE action with warning."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]
    snum = f"STU-UPD-{prefix}"

    csv1 = (
        f"student_number,first_name,last_name,admission_date\n{snum},Name,Initial,2025-01-01\n"
    ).encode()
    res1 = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "STUDENTS"},
        files={"file": ("s1.csv", io.BytesIO(csv1), "text/csv")},
    )
    job1_id = res1.json()["data"]["job"]["id"]
    client.post(f"/api/v1/imports/{job1_id}/commit", headers=headers, json={})

    # Import again with updated admission date
    csv2 = (
        f"student_number,first_name,last_name,admission_date\n{snum},Name,Updated,2026-09-01\n"
    ).encode()
    res2 = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "STUDENTS"},
        files={"file": ("s2.csv", io.BytesIO(csv2), "text/csv")},
    )
    assert res2.status_code == 201
    job2_id = res2.json()["data"]["job"]["id"]

    # Verify preview marked as UPDATE with warning
    rows_res = client.get(f"/api/v1/imports/{job2_id}/rows", headers=headers)
    row = rows_res.json()["data"]["items"][0]
    assert row["action"] == "UPDATE"
    assert row["status"] == ImportRowStatus.WARNING.value

    # Commit update
    commit_res = client.post(f"/api/v1/imports/{job2_id}/commit", headers=headers, json={})
    assert commit_res.status_code == 200

    # Verify updated in db
    s_stmt = select(Student).where(
        Student.university_id == test_university.id,
        Student.student_number == snum,
    )
    student = (await db_session.execute(s_stmt)).scalar_one_or_none()
    assert student is not None
    assert str(student.admission_date) == "2026-09-01"


@pytest.mark.asyncio
async def test_student_import_cancellation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify cancelling an import job prevents subsequent commit."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]
    snum = f"STU-CANCEL-{prefix}"

    csv_content = f"student_number,first_name,last_name\n{snum},A,B\n".encode()
    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "STUDENTS"},
        files={"file": ("s.csv", io.BytesIO(csv_content), "text/csv")},
    )
    job_id = res.json()["data"]["job"]["id"]

    cancel_res = client.post(f"/api/v1/imports/{job_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == ImportJobStatus.CANCELLED.value

    commit_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=headers, json={})
    assert commit_res.status_code == 409
