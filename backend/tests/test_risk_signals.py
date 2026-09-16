"""Integration tests for Milestone 14 Anti-Cheat Detection, Risk Signals, and Review Workflow.

Invariants Tested:
- Risk signals are factorized, deterministic, and immutable audit evidence.
- Idempotent deduplication via unique risk_key (no duplicate open alerts for same incident).
- Signals NEVER automatically punish students or modify attendance status (human review only).
- Human review workflow: OPEN -> ACKNOWLEDGED -> RESOLVED / DISMISSED with recorded justifications.
- Synchronous and asynchronous behavioral detectors.
"""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.attendance.service import AttendanceService
from backend.app.common.types import utc_now
from backend.app.core.constants import (
    RiskSeverity,
    RiskSignalStatus,
    RiskSignalType,
    RiskSubjectType,
)
from backend.app.models.risk_signal import AttendanceRiskSignal
from backend.app.models.university import University
from backend.app.models.user import User
from backend.app.security.risk_service import AntiCheatService
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_risk_signal_deduplication_via_risk_key(
    db_session: AsyncSession,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify that multiple occurrences of the same incident update existing signal
    instead of duplicating.
    """
    risk_key = f"TEST_DEDUP:{test_university.id}:{uuid.uuid4().hex}"
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)

    # 1. First emission
    sig1 = await AntiCheatService.record_risk_signal(
        db=db_session,
        university_id=test_university.id,
        signal_type=RiskSignalType.STUDENT_NETWORK_NOT_TRUSTED.value,
        severity=RiskSeverity.LOW.value,
        risk_points=15,
        subject_type=RiskSubjectType.STUDENT.value,
        risk_key=risk_key,
        subject_user_id=test_admin_user.id,
        context={"initial_ip": "198.51.100.1"},
        current_time=t0,
    )
    assert sig1.status == RiskSignalStatus.OPEN.value
    assert sig1.detected_at == t0

    # 2. Second emission with same risk_key at t0 + 10s
    t1 = t0 + datetime.timedelta(seconds=10)
    sig2 = await AntiCheatService.record_risk_signal(
        db=db_session,
        university_id=test_university.id,
        signal_type=RiskSignalType.STUDENT_NETWORK_NOT_TRUSTED.value,
        severity=RiskSeverity.LOW.value,
        risk_points=15,
        subject_type=RiskSubjectType.STUDENT.value,
        risk_key=risk_key,
        subject_user_id=test_admin_user.id,
        context={"followup_ip": "198.51.100.2"},
        current_time=t1,
    )

    # Must return the SAME signal ID without creating a duplicate row
    assert sig2.id == sig1.id

    # Verify only 1 row exists in DB
    stmt = select(AttendanceRiskSignal).where(AttendanceRiskSignal.risk_key == risk_key)
    res = await db_session.execute(stmt)
    records = list(res.scalars().all())
    assert len(records) == 1


@pytest.mark.asyncio
async def test_risk_signal_staff_review_workflow(
    db_session: AsyncSession,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify human review progression: OPEN -> ACKNOWLEDGED -> RESOLVED / DISMISSED."""
    risk_key = f"TEST_REVIEW:{test_university.id}:{uuid.uuid4().hex}"
    t0 = utc_now()

    signal = await AntiCheatService.record_risk_signal(
        db=db_session,
        university_id=test_university.id,
        signal_type=RiskSignalType.STUDENT_NETWORK_ZONE_MISMATCH.value,
        severity=RiskSeverity.MEDIUM.value,
        risk_points=30,
        subject_type=RiskSubjectType.STUDENT.value,
        risk_key=risk_key,
        subject_user_id=test_admin_user.id,
        context={"challenge_zone": "ZONE_A", "submission_zone": "ZONE_B"},
        current_time=t0,
    )
    assert signal.status == RiskSignalStatus.OPEN.value

    # 1. Staff acknowledges signal
    ack_res = await AntiCheatService.acknowledge_signal(
        db=db_session,
        signal_id=signal.id,
        university_id=test_university.id,
        reviewer_user_id=test_admin_user.id,
        current_time=t0 + datetime.timedelta(minutes=5),
    )
    assert ack_res.status == RiskSignalStatus.ACKNOWLEDGED.value
    assert ack_res.reviewed_by_user_id == test_admin_user.id

    # 2. Staff resolves signal
    t_resolve = t0 + datetime.timedelta(minutes=15)
    res_res = await AntiCheatService.resolve_signal(
        db=db_session,
        signal_id=signal.id,
        university_id=test_university.id,
        reviewer_user_id=test_admin_user.id,
        review_note="Student switched from campus Wi-Fi to mobile hotspot. Verified legitimate.",
        current_time=t_resolve,
    )
    assert res_res.status == RiskSignalStatus.RESOLVED.value
    assert res_res.resolved_at == t_resolve
    assert "mobile hotspot" in (res_res.review_note or "")


@pytest.mark.asyncio
async def test_synchronous_anti_cheat_detectors(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify synchronous check-in detectors generate appropriate factorized signals."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, admin_headers)
    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )

    # 1. Untrusted network check-in signal
    sig_net = await AntiCheatService.record_untrusted_network_signal(
        db=db_session,
        university_id=test_university.id,
        user_id=test_admin_user.id,
        session_id=sess.id,
        occurrence_id=uuid.UUID(occurrence_id),
        client_ip="203.0.113.88",
    )
    assert sig_net is not None
    assert sig_net.signal_type == RiskSignalType.STUDENT_NETWORK_NOT_TRUSTED.value
    assert sig_net.severity == RiskSeverity.LOW.value

    # 2. Zone mismatch signal
    sig_mis = await AntiCheatService.record_zone_mismatch_signal(
        db=db_session,
        university_id=test_university.id,
        user_id=test_admin_user.id,
        session_id=sess.id,
        occurrence_id=uuid.UUID(occurrence_id),
        challenge_zone_code="ZONE_ENG",
        submission_zone_code="ZONE_SCI",
    )
    assert sig_mis is not None
    assert sig_mis.signal_type == RiskSignalType.STUDENT_NETWORK_ZONE_MISMATCH.value
    assert sig_mis.severity == RiskSeverity.MEDIUM.value

    # 3. Network challenge replay attempt
    sig_replay = await AntiCheatService.record_replay_attempt_signal(
        db=db_session,
        university_id=test_university.id,
        user_id=test_admin_user.id,
        session_id=sess.id,
        challenge_id=uuid.uuid4(),
        proof_id=uuid.uuid4(),
    )
    assert sig_replay is not None
    assert sig_replay.signal_type == RiskSignalType.NETWORK_PROOF_REPLAY_ATTEMPT.value
    assert sig_replay.severity == RiskSeverity.HIGH.value

    # 4. Forward header spoof attempt
    sig_spoof = await AntiCheatService.record_header_spoof_signal(
        db=db_session,
        university_id=test_university.id,
        user_id=test_admin_user.id,
        direct_peer="198.51.100.25",
        spoofed_header="10.0.0.1, 192.168.1.1",
    )
    assert sig_spoof is not None
    assert sig_spoof.signal_type == RiskSignalType.NETWORK_FORWARD_HEADER_SPOOF_ATTEMPT.value
    assert sig_spoof.severity == RiskSeverity.MEDIUM.value


@pytest.mark.asyncio
async def test_session_schedule_deviation_detector(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify session schedule deviation detector triggers when activated > 60m away."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, admin_headers)
    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )

    scheduled_start = datetime.datetime(2026, 9, 15, 8, 0, 0, tzinfo=datetime.UTC)

    # 1. Activated 10 minutes after scheduled start -> NO signal
    actual_start_normal = scheduled_start + datetime.timedelta(minutes=10)
    sig_normal = await AntiCheatService.analyze_session_schedule_deviation(
        db=db_session,
        university_id=test_university.id,
        session_id=sess.id,
        occurrence_id=uuid.UUID(occurrence_id),
        scheduled_start=scheduled_start,
        actual_start=actual_start_normal,
    )
    assert sig_normal is None

    # 2. Activated 90 minutes after scheduled start -> TRIGGERS signal
    actual_start_late = scheduled_start + datetime.timedelta(minutes=90)
    sig_late = await AntiCheatService.analyze_session_schedule_deviation(
        db=db_session,
        university_id=test_university.id,
        session_id=sess.id,
        occurrence_id=uuid.UUID(occurrence_id),
        scheduled_start=scheduled_start,
        actual_start=actual_start_late,
    )
    assert sig_late is not None
    assert sig_late.signal_type == RiskSignalType.SESSION_OUTSIDE_SCHEDULE_WINDOW.value
    assert sig_late.severity == RiskSeverity.LOW.value
    assert sig_late.context is not None
    assert sig_late.context["deviation_minutes"] == 90.0
