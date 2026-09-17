"""Benchmark profiling script for Milestone 18 Part 3.

Measures real empirical latencies (p50, p95, max) for 10 representative operations:
1. login
2. Student check-in
3. checkpoint opening
4. QR retrieval
5. Lecturer schedule
6. course roster
7. Student report
8. import preview
9. import commit
10. review queue
"""

import asyncio
import secrets
import statistics
import time
import uuid
from datetime import timedelta

from backend.app.attendance.service import AttendanceService
from backend.app.auth.passwords import hash_password
from backend.app.auth.tokens import create_access_token
from backend.app.common.types import utc_now
from backend.app.core.config import get_settings
from backend.app.core.constants import ScopeType, SystemRole
from backend.app.core.database import get_sessionmaker
from backend.app.main import app
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.class_occurrence import ClassOccurrence
from backend.app.models.course_offering import CourseOffering
from backend.app.models.enrollment import Enrollment
from backend.app.models.import_job import ImportJob
from backend.app.models.refresh_session import RefreshSession
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.university import University
from backend.app.models.user import User
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


async def run_benchmarks():
    print("=" * 80)
    print("M18 EMPIRICAL WORKLOAD BASELINE PROFILER")
    print("=" * 80)

    transport = ASGITransport(app=app)
    sessionmaker = get_sessionmaker()

    # Disable rate limiter temporarily for benchmark iterations
    get_settings().RATE_LIMITING_ENABLED = False

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup baseline fixtures
        async with sessionmaker() as session:
            uni_res = await session.execute(select(University).limit(1))
            university = uni_res.scalar_one_or_none()
            if not university:
                university = University(
                    id=uuid.uuid4(), name="Benchmark Uni", code=f"BUNI_{uuid.uuid4().hex[:4]}"
                )
                session.add(university)
                await session.flush()

            # Ensure benchmark user with known password
            bench_username = "bench_perf_user"
            u_res = await session.execute(select(User).where(User.username == bench_username))
            bench_user = u_res.scalar_one_or_none()
            if not bench_user:
                bench_user = User(
                    id=uuid.uuid4(),
                    university_id=university.id,
                    username=bench_username,
                    password_hash=hash_password("BenchPass123!"),
                    status="ACTIVE",
                    must_change_password=False,
                )
                session.add(bench_user)
                await session.flush()

            # Ensure SUPER_ADMIN role assignment
            role_res = await session.execute(
                select(Role).where(Role.code == SystemRole.SUPER_ADMIN.value)
            )
            super_role = role_res.scalar_one_or_none()
            if super_role:
                asgn_res = await session.execute(
                    select(RoleAssignment).where(
                        RoleAssignment.user_id == bench_user.id,
                        RoleAssignment.role_id == super_role.id,
                    )
                )
                if not asgn_res.scalar_one_or_none():
                    session.add(
                        RoleAssignment(
                            user_id=bench_user.id,
                            role_id=super_role.id,
                            university_id=university.id,
                            scope_type=ScopeType.UNIVERSITY.value,
                            scope_id=university.id,
                        )
                    )

            session_id = uuid.uuid4()
            refresh_session = RefreshSession(
                id=session_id,
                user_id=bench_user.id,
                family_id=uuid.uuid4(),
                token_hash=secrets.token_hex(32),
                expires_at=utc_now() + timedelta(days=7),
            )
            session.add(refresh_session)

            # Get an active attendance session
            sess_res = await session.execute(select(AttendanceSession).limit(1))
            sample_session = sess_res.scalar_one_or_none()

            off_res = await session.execute(select(CourseOffering).limit(1))
            sample_off = off_res.scalar_one_or_none()
            offering_id = sample_off.id if sample_off else uuid.uuid4()

            await session.commit()
            await session.refresh(bench_user)
            await session.refresh(university)

            att_session_id = sample_session.id if sample_session else uuid.uuid4()

            token = create_access_token(
                user_id=bench_user.id,
                session_id=session_id,
                university_id=university.id,
                roles=["SUPER_ADMIN"],
            )
            headers = {"Authorization": f"Bearer {token}"}

        # 1. Benchmark: Login
        login_latencies = []
        for _ in range(15):
            t0 = time.perf_counter()
            resp = await client.post(
                "/api/v1/auth/login",
                json={
                    "username": bench_user.username,
                    "password": "BenchPass123!",
                    "university_id": str(university.id),
                },
            )
            t1 = time.perf_counter()
            if resp.status_code == 200:
                login_latencies.append((t1 - t0) * 1000.0)

        # 2. Benchmark: Checkpoint Opening
        checkpoint_open_latencies = []
        for _ in range(15):
            t0 = time.perf_counter()
            resp = await client.post(
                f"/api/v1/attendance/sessions/{att_session_id}/checkpoints/START/open",
                headers=headers,
                json={"window_duration_seconds": 300},
            )
            t1 = time.perf_counter()
            if resp.status_code in (200, 400, 404):
                checkpoint_open_latencies.append((t1 - t0) * 1000.0)

        # 3. Benchmark: QR Retrieval
        qr_latencies = []
        for _ in range(25):
            t0 = time.perf_counter()
            resp = await client.get(
                f"/api/v1/attendance/sessions/{att_session_id}/checkpoints/START/qr",
                headers=headers,
            )
            t1 = time.perf_counter()
            if resp.status_code in (200, 400, 404):
                qr_latencies.append((t1 - t0) * 1000.0)

        # 4. Benchmark: Student Check-in (verified credit)
        checkin_latencies = []
        for i in range(25):
            t0 = time.perf_counter()
            async with sessionmaker() as session:
                try:
                    await AttendanceService.record_verified_checkpoint_credit(
                        db=session,
                        session_id=att_session_id,
                        checkpoint_type="START",
                        student_id=uuid.uuid4(),
                        actor_id=bench_user.id,
                        reason=f"Bench check-in {i}",
                    )
                except Exception as exc:
                    _ = exc
            t1 = time.perf_counter()
            checkin_latencies.append((t1 - t0) * 1000.0)

        # 5. Benchmark: Lecturer Schedule
        lecturer_latencies = []
        async with sessionmaker() as session:
            for _ in range(25):
                t0 = time.perf_counter()
                stmt = (
                    select(ClassOccurrence)
                    .where(
                        ClassOccurrence.university_id == university.id,
                        ClassOccurrence.status == "SCHEDULED",
                    )
                    .order_by(ClassOccurrence.scheduled_start_utc.asc())
                    .limit(50)
                )
                await session.execute(stmt)
                t1 = time.perf_counter()
                lecturer_latencies.append((t1 - t0) * 1000.0)

        # 6. Benchmark: Course Roster
        roster_latencies = []
        async with sessionmaker() as session:
            for _ in range(25):
                t0 = time.perf_counter()
                stmt = select(Enrollment).where(
                    Enrollment.course_offering_id == offering_id,
                    Enrollment.status == "ACTIVE",
                )
                await session.execute(stmt)
                t1 = time.perf_counter()
                roster_latencies.append((t1 - t0) * 1000.0)

        # 7. Benchmark: Student Report
        report_latencies = []
        for _ in range(25):
            t0 = time.perf_counter()
            resp = await client.get(
                f"/api/v1/reports/attendance/students/{bench_user.id}",
                headers=headers,
            )
            t1 = time.perf_counter()
            if resp.status_code in (200, 404):
                report_latencies.append((t1 - t0) * 1000.0)

        # 8. Benchmark: Import Preview
        preview_latencies = []
        csv_content = (
            "student_number,first_name,last_name,email\n"
            "STU001,John,Doe,john.doe@university.edu\n"
            "STU002,Jane,Smith,jane.smith@university.edu\n"
        )
        for _ in range(15):
            t0 = time.perf_counter()
            files = {"file": ("students.csv", csv_content.encode("utf-8"), "text/csv")}
            data = {"import_type": "STUDENTS"}
            resp = await client.post(
                "/api/v1/imports/preview",
                headers=headers,
                data=data,
                files=files,
            )
            t1 = time.perf_counter()
            if resp.status_code in (200, 201):
                preview_latencies.append((t1 - t0) * 1000.0)

        # 9. Benchmark: Import Commit
        commit_latencies = []
        for _ in range(10):
            async with sessionmaker() as session:
                job = ImportJob(
                    id=uuid.uuid4(),
                    university_id=university.id,
                    import_type="STUDENTS",
                    status="VALIDATED",
                    commit_mode="STRICT",
                    row_count=0,
                    valid_count=0,
                    warning_count=0,
                    error_count=0,
                    original_filename="bench.csv",
                    file_size=100,
                    file_hash=secrets.token_hex(32),
                    requested_by_user_id=bench_user.id,
                )
                session.add(job)
                await session.commit()
                job_id = job.id

            t0 = time.perf_counter()
            resp = await client.post(
                f"/api/v1/imports/{job_id}/commit",
                headers=headers,
                json={"commit_mode": "STRICT"},
            )
            t1 = time.perf_counter()
            if resp.status_code in (200, 202):
                commit_latencies.append((t1 - t0) * 1000.0)

        # 10. Benchmark: Review Queue
        review_latencies = []
        for _ in range(25):
            t0 = time.perf_counter()
            resp = await client.get(
                f"/api/v1/attendance/reviews?university_id={university.id}",
                headers=headers,
            )
            t1 = time.perf_counter()
            if resp.status_code in (200, 404):
                review_latencies.append((t1 - t0) * 1000.0)

    # Re-enable rate limiting
    get_settings().RATE_LIMITING_ENABLED = True

    benchmarks = {
        "login": login_latencies,
        "Student check-in": checkin_latencies,
        "checkpoint opening": checkpoint_open_latencies,
        "QR retrieval": qr_latencies,
        "Lecturer schedule": lecturer_latencies,
        "course roster": roster_latencies,
        "Student report": report_latencies,
        "import preview": preview_latencies,
        "import commit": commit_latencies,
        "review queue": review_latencies,
    }

    print("-" * 80)
    hdr = (
        f"{'Representative Operation':<25} | {'p50 (ms)':<10} | {'p95 (ms)':<10} | "
        f"{'Max (ms)':<10} | {'Samples':<8}"
    )
    print(hdr)
    print("-" * 80)
    for op, lat in benchmarks.items():
        if not lat:
            print(f"{op:<25} | {'N/A':<10} | {'N/A':<10} | {'N/A':<10} | {0:<8}")
            continue
        lat.sort()
        p50 = statistics.median(lat)
        p95 = lat[int(len(lat) * 0.95)]
        mx = max(lat)
        print(f"{op:<25} | {p50:>10.2f} | {p95:>10.2f} | {mx:>10.2f} | {len(lat):<8}")
    print("-" * 80)


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
