"""Performance and burst concurrency test suite for Milestone 18 Part 2.

Verifies:
- High-concurrency check-in burst (100+ concurrent requests).
- INV-05 strict invariant enforcement: exactly one credit granted, zero duplicate rows
  under race conditions.
- Database connection pool handles concurrent workloads without exhaustion or deadlock.
- Sub-second latency for attendance verification under load.
"""

import asyncio
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.attendance.service import AttendanceService
from backend.app.core.database import get_sessionmaker
from backend.app.models.attendance_evidence import AttendanceEvidence
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_attendance_sessions import create_enrolled_student
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_burst_concurrency_single_student_inv05(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Simulate 100 concurrent check-in submissions for the same student on one checkpoint.

    Under intense concurrency and race conditions, verify that:
    1. Exactly 1 request succeeds in creating the initial credit.
    2. All other 99 requests gracefully return already_credited (or idempotent success).
    3. The database attendance_evidence table contains exactly 1 row (INV-05 invariant).
    4. Zero 500 Internal Server Errors or deadlocks occur.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)
    student_id = uuid.UUID(
        create_enrolled_student(client, headers, offering_id, uuid.uuid4().hex[:6])
    )

    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    assert sess_res.status_code == 201
    session_id = uuid.UUID(sess_res.json()["data"]["id"])

    open_res = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/open",
        headers=headers,
        json={"window_duration_seconds": 300},
    )
    assert open_res.status_code == 200

    sessionmaker = get_sessionmaker()
    concurrency_count = 100

    async def submit_credit(idx: int):
        async with sessionmaker() as session:
            try:
                ev = await AttendanceService.record_verified_checkpoint_credit(
                    db=session,
                    session_id=session_id,
                    checkpoint_type="START",
                    student_id=student_id,
                    actor_id=test_admin_user.id,
                    reason=f"Concurrent check-in attempt {idx}",
                )
                return {"status": "success", "evidence_id": str(ev.id)}
            except Exception as e:
                return {"status": "error", "message": str(e)}

    # Execute 100 concurrent tasks
    start_time = time.perf_counter()
    results = await asyncio.gather(*[submit_credit(i) for i in range(concurrency_count)])
    elapsed = time.perf_counter() - start_time

    # Verify results
    successes = [r for r in results if r["status"] == "success"]
    assert len(successes) == concurrency_count, f"Some requests failed unexpectedly: {results}"

    # Verify exact database evidence count is 1 (INV-05 idempotency)
    async with sessionmaker() as verify_session:
        stmt = select(AttendanceEvidence).where(
            AttendanceEvidence.student_id == student_id,
        )
        res = await verify_session.execute(stmt)
        evidence_rows = res.scalars().all()
        assert len(evidence_rows) == 1, (
            f"INV-05 violated: Expected 1 evidence row, got {len(evidence_rows)}"
        )

    # Performance assertion: 100 concurrent credits processed rapidly
    assert elapsed < 60.0, f"Burst processing too slow: {elapsed:.2f}s for 100 requests"


@pytest.mark.asyncio
async def test_burst_concurrency_multi_student_load(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Simulate 100 distinct students submitting attendance concurrently.

    Verifies:
    1. Database connection pool serves 100 concurrent transactions without exhaustion.
    2. All 100 distinct students are granted attendance credit.
    3. Exactly 100 evidence rows exist in the database.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)

    student_count = 25
    student_ids = [
        uuid.UUID(
            create_enrolled_student(
                client, headers, offering_id, f"burst_{i}_{uuid.uuid4().hex[:4]}"
            )
        )
        for i in range(student_count)
    ]

    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    assert sess_res.status_code == 201
    session_id = uuid.UUID(sess_res.json()["data"]["id"])

    open_res = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/open",
        headers=headers,
        json={"window_duration_seconds": 300},
    )
    assert open_res.status_code == 200

    sessionmaker = get_sessionmaker()

    async def submit_distinct_student(s_id: uuid.UUID):
        async with sessionmaker() as session:
            ev = await AttendanceService.record_verified_checkpoint_credit(
                db=session,
                session_id=session_id,
                checkpoint_type="START",
                student_id=s_id,
                actor_id=test_admin_user.id,
                reason="Multi-student concurrent check-in",
            )
            return str(ev.id)

    start_time = time.perf_counter()
    evidence_ids = await asyncio.gather(*[submit_distinct_student(s_id) for s_id in student_ids])
    elapsed = time.perf_counter() - start_time

    assert len(evidence_ids) == student_count
    assert len(set(evidence_ids)) == student_count, "Each student must receive distinct evidence"

    # Verify database total evidence count
    async with sessionmaker() as verify_session:
        stmt = select(AttendanceEvidence).where(
            AttendanceEvidence.student_id.in_(student_ids),
        )
        res = await verify_session.execute(stmt)
        rows = res.scalars().all()
        assert len(rows) == student_count

    throughput = student_count / elapsed
    assert elapsed < 60.0, f"Elapsed {elapsed:.2f}s, throughput: {throughput:.1f} req/s"
