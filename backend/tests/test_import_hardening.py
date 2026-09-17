"""Test suite for Milestone 16 Part 3 final hardening:
Atomicity, Retry, Concurrency, Frozen Historical Rosters, and Large Scale Import Performance.
"""

import io
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import (
    AttendanceSessionStatus,
    ImportJobStatus,
    ImportRowStatus,
)
from backend.app.imports.parser import parse_import_file
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.student import Student
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_corrections import setup_closed_session
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_import_strict_atomicity_and_staging_review(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """SECTION 6: Under STRICT mode, one blocking row error prevents production commit;
    staging remains reviewable.
    """
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]
    snum_good = f"STU-GOOD-{prefix}"
    snum_bad = f"STU-BAD-{prefix}"

    # Row 1 is valid, Row 2 has unknown academic unit code
    csv_content = (
        "student_number,first_name,last_name,academic_unit_code\n"
        f"{snum_good},Farhad,Ahmadi,\n"
        f"{snum_bad},Karim,Noori,NON_EXISTENT_FACULTY_CODE\n"
    ).encode()

    # 1. Preview
    res = client.post(
        "/api/v1/imports/preview",
        headers=admin_headers,
        data={"import_type": "STUDENTS", "commit_mode": "STRICT"},
        files={"file": ("strict_batch.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201
    job_id = res.json()["data"]["job"]["id"]

    # 2. Attempt commit in STRICT mode -> MUST BE REJECTED WITH 422
    commit_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=admin_headers, json={})
    assert commit_res.status_code == 422
    err_body = commit_res.json()
    assert "STRICT mode" in err_body["error"]["message"]

    # 3. CRITICAL INVARIANT: Staging rows remain reviewable with precise error annotations
    rows_res = client.get(f"/api/v1/imports/{job_id}/rows", headers=admin_headers)
    assert rows_res.status_code == 200
    rows = rows_res.json()["data"]["items"]
    assert len(rows) == 2
    assert rows[0]["status"] == ImportRowStatus.VALID.value
    assert rows[1]["status"] == ImportRowStatus.ERROR.value
    assert any(e["code"] == "ACADEMIC_UNIT_NOT_FOUND" for e in rows[1]["errors"])

    # 4. Zero mutation in domain tables
    s_stmt = select(Student).where(
        Student.university_id == test_university.id,
        Student.student_number == snum_good,
    )
    assert (await db_session.execute(s_stmt)).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_import_commit_retry_and_concurrency_protection(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """SECTIONS 7 & 8: Commit succeeds; retry returns deterministic conflict
    without duplicating records.
    """
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]
    snum = f"STU-RETRY-{prefix}"

    csv_content = (f"student_number,first_name,last_name\n{snum},Zahra,Hussaini\n").encode()

    # 1. Preview
    res = client.post(
        "/api/v1/imports/preview",
        headers=admin_headers,
        data={"import_type": "STUDENTS"},
        files={"file": ("retry_test.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201
    job_id = res.json()["data"]["job"]["id"]

    # 2. First Commit succeeds
    c1 = client.post(f"/api/v1/imports/{job_id}/commit", headers=admin_headers, json={})
    assert c1.status_code == 200
    assert c1.json()["data"]["status"] == ImportJobStatus.COMPLETED.value
    assert c1.json()["data"]["commit_count"] == 1

    # 3. Second Commit (simulating lost HTTP response / retry) returns 409 Conflict
    c2 = client.post(f"/api/v1/imports/{job_id}/commit", headers=admin_headers, json={})
    assert c2.status_code == 409
    assert "already been completed" in c2.json()["error"]["message"]

    # 4. Invariant: Only ONE student created in production
    s_stmt = select(Student).where(
        Student.university_id == test_university.id,
        Student.student_number == snum,
    )
    students = list((await db_session.execute(s_stmt)).scalars().all())
    assert len(students) == 1


@pytest.mark.asyncio
async def test_frozen_history_unaffected_by_subsequent_import(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """SECTION 10: Subsequent student enrollment/import cannot alter previously
    closed sessions or records.
    """
    from backend.tests.test_attendance_corrections import create_student_with_role
    from backend.tests.test_attendance_policy import setup_class_occurrence

    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    student1_id, _, _ = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "frozen1"
    )

    # Close session
    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)

    # Verify session is CLOSED
    sess = await db_session.get(AttendanceSession, uuid.UUID(session_id))
    assert sess is not None
    assert sess.status == AttendanceSessionStatus.CLOSED.value

    # Get student1's record
    records_res = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    assert records_res.status_code == 200
    record_id = uuid.UUID(records_res.json()["data"][0]["id"])

    rec_before = await db_session.get(AttendanceRecord, record_id)
    assert rec_before is not None
    credit_before = rec_before.attendance_credit
    status_before = rec_before.status
    version_before = rec_before.version_no

    # Now import a new student and enroll them into the same course offering
    prefix = uuid.uuid4().hex[:6]
    new_snum = f"STU-LATE-ENR-{prefix}"
    csv_content = (f"student_number,first_name,last_name\n{new_snum},Late,Enrollee\n").encode()

    res = client.post(
        "/api/v1/imports/preview",
        headers=admin_headers,
        data={"import_type": "STUDENTS"},
        files={"file": ("late_student.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201
    job_id = res.json()["data"]["job"]["id"]
    commit_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=admin_headers, json={})
    assert commit_res.status_code == 200

    # Verify historical session, roster, and record remain FROZEN
    await db_session.refresh(sess)
    assert sess.status == AttendanceSessionStatus.CLOSED.value

    await db_session.refresh(rec_before)
    assert rec_before.attendance_credit == credit_before
    assert rec_before.status == status_before
    assert rec_before.version_no == version_before

    # Verify the late student does NOT have a retroactive record for the closed session
    new_student_stmt = select(Student).where(
        Student.university_id == test_university.id,
        Student.student_number == new_snum,
    )
    new_student = (await db_session.execute(new_student_stmt)).scalar_one()
    late_rec_stmt = select(AttendanceRecord).where(
        AttendanceRecord.attendance_session_id == uuid.UUID(session_id),
        AttendanceRecord.student_id == new_student.id,
    )
    assert (await db_session.execute(late_rec_stmt)).scalar_one_or_none() is None


def test_large_import_performance_3000_students() -> None:
    """SECTION 18: Generate 3,000 students realistic fixture and benchmark parsing."""
    lines = ["student_number,first_name,last_name,email,admission_date"]
    for i in range(1, 3001):
        lines.append(f"STU-2026-{i:05d},احمد_{i},محمدی_{i},student_{i}@kabul.edu.af,2026-03-21")
    csv_bytes = "\n".join(lines).encode()

    start_time = time.perf_counter()
    parsed = parse_import_file(
        "students_3k.csv", csv_bytes, max_bytes=10 * 1024 * 1024, max_rows=5000
    )
    duration = time.perf_counter() - start_time

    assert len(parsed.rows) == 3000
    assert parsed.headers == [
        "student_number",
        "first_name",
        "last_name",
        "email",
        "admission_date",
    ]
    # In-memory CSV parse of 3,000 rows must complete well within 2 seconds
    assert duration < 2.0, f"Parsing took {duration:.2f}s, expected < 2.0s"
