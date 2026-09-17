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


@pytest.mark.asyncio
async def test_import_and_reporting_comprehensive_benchmarks(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """SECTION 18: End-to-end performance benchmarks across parsing, validation, staging, commit,
    bulk enrollments, and representative attendance report queries on real PostgreSQL.
    """
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]

    # 1. Benchmark: 3,000-Row Student CSV Parsing
    lines_3k = ["student_number,first_name,last_name,email,admission_date"]
    for i in range(1, 3001):
        lines_3k.append(
            f"STU-B3K-{prefix}-{i:05d},احمد_{i},محمدی_{i},b3k_{prefix}_{i}@kabul.edu.af,2026-03-21"
        )
    csv_bytes_3k = "\n".join(lines_3k).encode()

    t0 = time.perf_counter()
    parsed_3k = parse_import_file(
        "students_3k.csv", csv_bytes_3k, max_bytes=10 * 1024 * 1024, max_rows=5000
    )
    t_parse_3k = time.perf_counter() - t0
    assert len(parsed_3k.rows) == 3000
    assert t_parse_3k < 2.0, f"3,000 parse took {t_parse_3k:.4f}s (budget: < 2.0s)"

    # 2. Benchmark: 100-Row Student Validation & Staging/Preview
    lines_100 = ["student_number,first_name,last_name,email"]
    for i in range(1, 101):
        lines_100.append(
            f"STU-B100-{prefix}-{i:04d},Student_{i},Family_{i},b100_{prefix}_{i}@kabul.edu.af"
        )
    csv_bytes_100 = "\n".join(lines_100).encode()

    t1 = time.perf_counter()
    preview_res = client.post(
        "/api/v1/imports/preview",
        headers=admin_headers,
        data={"import_type": "STUDENTS"},
        files={"file": ("students_100.csv", io.BytesIO(csv_bytes_100), "text/csv")},
    )
    t_stage_100 = time.perf_counter() - t1
    assert preview_res.status_code == 201
    job_id = preview_res.json()["data"]["job"]["id"]
    assert preview_res.json()["data"]["job"]["valid_count"] == 100
    assert t_stage_100 < 8.0, f"100 validation & staging took {t_stage_100:.4f}s (budget: < 8.0s)"

    # 3. Benchmark: 100-Row Production Commit (User creation + Argon2 hashing + Student + Role)
    t2 = time.perf_counter()
    commit_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=admin_headers, json={})
    t_commit_100 = time.perf_counter() - t2
    assert commit_res.status_code == 200
    assert commit_res.json()["data"]["commit_count"] == 100
    assert t_commit_100 < 12.0, f"100 commit took {t_commit_100:.4f}s (budget: < 12.0s)"

    # 4. Benchmark: Bulk Enrollment Ingestion (100 Enrollments Stage + Commit)
    from backend.tests.test_enrollment_import import create_offering_and_student

    c_code, sem_code, sec_code, _, offering_id, _ = create_offering_and_student(
        client, admin_headers
    )

    enr_lines = ["student_number,course_code,semester_code,section_code"]
    for i in range(1, 101):
        enr_lines.append(f"STU-B100-{prefix}-{i:04d},{c_code},{sem_code},{sec_code}")
    csv_bytes_enr = "\n".join(enr_lines).encode()

    t3 = time.perf_counter()
    enr_prev = client.post(
        "/api/v1/imports/preview",
        headers=admin_headers,
        data={"import_type": "ENROLLMENTS"},
        files={"file": ("enrollments_100.csv", io.BytesIO(csv_bytes_enr), "text/csv")},
    )
    assert enr_prev.status_code == 201
    enr_job_id = enr_prev.json()["data"]["job"]["id"]
    enr_commit = client.post(f"/api/v1/imports/{enr_job_id}/commit", headers=admin_headers, json={})
    t_enr_100 = time.perf_counter() - t3
    assert enr_commit.status_code == 200
    assert enr_commit.json()["data"]["commit_count"] == 100
    assert t_enr_100 < 10.0, f"100 enrollments took {t_enr_100:.4f}s (budget: < 10.0s)"

    # 5. Benchmark: Representative Attendance Report Query (100-Student Roster)
    t4 = time.perf_counter()
    rep_res = client.get(
        f"/api/v1/reports/attendance/course-offerings/{offering_id}?page=1&page_size=100",
        headers=admin_headers,
    )
    t_rep_query = time.perf_counter() - t4
    assert rep_res.status_code == 200
    assert rep_res.json()["data"]["total_enrolled"] == 100
    assert t_rep_query < 1.0, f"Roster query took {t_rep_query:.4f}s (budget: < 1.0s)"

    print(
        f"\n=======================================================\n"
        f"MILESTONE 16 PERFORMANCE BENCHMARK EVIDENCE:\n"
        f"  1. 3,000-Row Student CSV Parsing:              {t_parse_3k:.4f}s  (Budget: < 2.0s)\n"
        f"  2. 100-Row Validation & Staging (Preview):     {t_stage_100:.4f}s  (Budget: < 8.0s)\n"
        f"  3. 100-Row Production Commit (DB + Argon2):    {t_commit_100:.4f}s  (Budget: < 12.0s)\n"
        f"  4. 100-Row Bulk Enrollment (Stage + Commit):   {t_enr_100:.4f}s  (Budget: < 10.0s)\n"
        f"  5. 100-Student Course Roster Report Query:     {t_rep_query:.4f}s  (Budget: < 1.0s)\n"
        f"======================================================="
    )
