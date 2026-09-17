"""Integration tests for Lecturer Data Import, Validation, Preview, and Safe Commit."""

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
    LecturerStatus,
)
from backend.app.models.lecturer import Lecturer
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_lecturer_import_preview_non_mutation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """INVARIANT: Preview MUST NEVER mutate production domain tables (lecturers, users)."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]
    emp_code = f"LEC-PREV-{prefix}"

    csv_content = (
        "employee_code,first_name,last_name,email,title\n"
        f"{emp_code},استاد نورالله,کریمی,lec_prev_{prefix}@kabul.edu.af,Assistant Professor\n"
    ).encode()

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "LECTURERS", "commit_mode": "STRICT"},
        files={"file": ("lecturers_preview.csv", io.BytesIO(csv_content), "text/csv")},
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

    # CRITICAL INVARIANT: Production tables must NOT contain this lecturer or user
    lec_stmt = select(Lecturer).where(
        Lecturer.university_id == test_university.id,
        Lecturer.employee_code == emp_code,
    )
    assert (await db_session.execute(lec_stmt)).scalar_one_or_none() is None

    u_stmt = select(User).where(
        User.university_id == test_university.id,
        User.username == emp_code.lower().replace("-", "_"),
    )
    assert (await db_session.execute(u_stmt)).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_lecturer_import_commit_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify committing staged lecturers creates User, assigns Role, and creates Lecturer."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]
    emp_code = f"LEC-COMMIT-{prefix}"
    expected_username = emp_code.lower().replace("-", "_")

    csv_content = (
        "employee_code,first_name,last_name,email,phone,title,status\n"
        f"{emp_code},احمد,نوری,lec_{prefix}@kabul.edu.af,+93700998877,Assoc Prof,ACTIVE\n"
    ).encode()

    # 1. Preview
    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "LECTURERS", "commit_mode": "STRICT"},
        files={"file": ("lecturers.csv", io.BytesIO(csv_content), "text/csv")},
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
    lec_stmt = select(Lecturer).where(
        Lecturer.university_id == test_university.id,
        Lecturer.employee_code == emp_code,
    )
    lecturer = (await db_session.execute(lec_stmt)).scalar_one_or_none()
    assert lecturer is not None
    assert lecturer.title == "Assoc Prof"
    assert lecturer.status == LecturerStatus.ACTIVE.value

    user = await db_session.get(User, lecturer.user_id)
    assert user is not None
    assert user.username == expected_username
    assert user.email == f"lec_{prefix}@kabul.edu.af"
    assert user.must_change_password is True

    # Verify role assignment
    ra_stmt = select(RoleAssignment).where(
        RoleAssignment.user_id == user.id,
        RoleAssignment.university_id == test_university.id,
    )
    assignments = list((await db_session.execute(ra_stmt)).scalars().all())
    assert len(assignments) >= 1

    # Double commit must be rejected
    double_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=headers, json={})
    assert double_res.status_code == 409


@pytest.mark.asyncio
async def test_lecturer_import_intra_file_duplicate_and_unknown_unit(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify intra-file duplicate employee codes and non-existent units produce row errors."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]
    dup_code = f"LEC-DUP-{prefix}"

    csv_content = (
        "employee_code,first_name,last_name,academic_unit_code\n"
        f"{dup_code},Dr,Alpha,NON_EXISTENT_UNIT\n"
        f"{dup_code},Dr,Beta,NON_EXISTENT_UNIT\n"
    ).encode()

    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "LECTURERS", "commit_mode": "STRICT"},
        files={"file": ("dup_lecturers.csv", io.BytesIO(csv_content), "text/csv")},
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
async def test_lecturer_import_update_existing_lecturer(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify importing an existing lecturer updates their profile information."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]
    emp_code = f"LEC-UPD-{prefix}"

    # First import: create lecturer
    csv_v1 = (
        "employee_code,first_name,last_name,email,title,status\n"
        f"{emp_code},Zahra,Hakimi,zahra_{prefix}@kabul.edu.af,Lecturer,ACTIVE\n"
    ).encode()

    res1 = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "LECTURERS"},
        files={"file": ("v1.csv", io.BytesIO(csv_v1), "text/csv")},
    )
    assert res1.status_code == 201
    job1_id = res1.json()["data"]["job"]["id"]
    client.post(f"/api/v1/imports/{job1_id}/commit", headers=headers, json={})

    # Second import: update title and status
    csv_v2 = (
        "employee_code,first_name,last_name,email,title,status\n"
        f"{emp_code},Zahra,Hakimi-Kakar,zahra_{prefix}@kabul.edu.af,Assistant Professor,ON_LEAVE\n"
    ).encode()

    res2 = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "LECTURERS"},
        files={"file": ("v2.csv", io.BytesIO(csv_v2), "text/csv")},
    )
    assert res2.status_code == 201
    job2_id = res2.json()["data"]["job"]["id"]

    # Verify action is UPDATE and row status is WARNING
    rows_res = client.get(f"/api/v1/imports/{job2_id}/rows", headers=headers)
    rows = rows_res.json()["data"]["items"]
    assert rows[0]["action"] == ImportRowAction.UPDATE.value
    assert rows[0]["status"] == ImportRowStatus.WARNING.value

    # Commit update
    commit_res = client.post(f"/api/v1/imports/{job2_id}/commit", headers=headers, json={})
    assert commit_res.status_code == 200

    # Verify database update
    lec_stmt = select(Lecturer).where(
        Lecturer.university_id == test_university.id,
        Lecturer.employee_code == emp_code,
    )
    updated_lec = (await db_session.execute(lec_stmt)).scalar_one()
    assert updated_lec.title == "Assistant Professor"
    assert updated_lec.status == LecturerStatus.ON_LEAVE.value
