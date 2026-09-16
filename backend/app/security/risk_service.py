"""Anti-Cheat Risk Signal Service implementing deterministic, factorized fraud detection rules.

Invariants Enforced:
- Anti-cheat signals are review records for human administrators (Section 1 & 3).
- Signals NEVER automatically mark students Absent, revoke credits, or discipline accounts.
- Zero black-box ML: rules are deterministic, explainable, factorized, and versioned.
- Idempotency guaranteed via unique risk_key per university.
- Status workflow: OPEN -> ACKNOWLEDGED -> RESOLVED or DISMISSED.
"""

import datetime
import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.types import utc_now
from backend.app.core.config import get_settings
from backend.app.core.constants import (
    AttendanceStatus,
    DeviceReplacementStatus,
    RiskSeverity,
    RiskSignalStatus,
    RiskSignalType,
    RiskSubjectType,
)
from backend.app.core.exceptions import NotFoundException
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.attendance_revision import AttendanceRevision
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.class_occurrence import ClassOccurrence
from backend.app.models.risk_signal import AttendanceRiskSignal
from backend.app.models.trusted_device import DeviceReplacementRequest
from backend.app.security.schemas import AttendanceRiskSignalResponse

logger = logging.getLogger(__name__)

RULE_VERSION = "1.0"


class AntiCheatService:
    """Service detecting, persisting, and managing anti-cheat risk signals for human review."""

    # =========================================================================
    # 1. Idempotent Risk Signal Persistence
    # =========================================================================

    @staticmethod
    async def record_risk_signal(
        db: AsyncSession,
        university_id: uuid.UUID,
        signal_type: str,
        severity: str,
        risk_points: int,
        subject_type: str,
        risk_key: str,
        subject_user_id: uuid.UUID | None = None,
        trusted_device_id: uuid.UUID | None = None,
        attendance_session_id: uuid.UUID | None = None,
        class_occurrence_id: uuid.UUID | None = None,
        course_offering_id: uuid.UUID | None = None,
        context: dict[str, Any] | None = None,
        current_time: datetime.datetime | None = None,
    ) -> AttendanceRiskSignal:
        """Persist an explainable risk signal with idempotent duplicate prevention via risk_key."""
        now = current_time or utc_now()

        # Check existing signal by risk_key
        stmt = select(AttendanceRiskSignal).where(
            AttendanceRiskSignal.university_id == university_id,
            AttendanceRiskSignal.risk_key == risk_key,
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            # Signal already recorded for this rule/entity/window
            return existing

        signal = AttendanceRiskSignal(
            university_id=university_id,
            signal_type=signal_type,
            severity=severity,
            risk_points=risk_points,
            subject_type=subject_type,
            subject_user_id=subject_user_id,
            trusted_device_id=trusted_device_id,
            attendance_session_id=attendance_session_id,
            class_occurrence_id=class_occurrence_id,
            course_offering_id=course_offering_id,
            context=context or {},
            rule_version=RULE_VERSION,
            risk_key=risk_key,
            detected_at=now,
            status=RiskSignalStatus.OPEN.value,
            created_at=now,
            updated_at=now,
        )
        db.add(signal)
        await db.flush()
        return signal

    # =========================================================================
    # 2. Synchronous Check-In & Request Detectors
    # =========================================================================

    @classmethod
    async def record_untrusted_network_signal(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        occurrence_id: uuid.UUID | None,
        client_ip: str,
        trusted_device_id: uuid.UUID | None = None,
    ) -> AttendanceRiskSignal:
        """Triggered when student checks in from an unverified network in OPTIONAL mode."""
        risk_key = f"UNT_NET:{university_id}:{user_id}:{session_id}"
        return await cls.record_risk_signal(
            db=db,
            university_id=university_id,
            signal_type=RiskSignalType.STUDENT_NETWORK_NOT_TRUSTED.value,
            severity=RiskSeverity.LOW.value,
            risk_points=15,
            subject_type=RiskSubjectType.STUDENT.value,
            risk_key=risk_key,
            subject_user_id=user_id,
            trusted_device_id=trusted_device_id,
            attendance_session_id=session_id,
            class_occurrence_id=occurrence_id,
            context={
                "rule": "STUDENT_NETWORK_NOT_TRUSTED",
                "observed_ip": client_ip,
                "reason": "Attendance recorded without verified trusted campus network presence.",
            },
        )

    @classmethod
    async def record_zone_mismatch_signal(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        occurrence_id: uuid.UUID | None,
        challenge_zone_code: str,
        submission_zone_code: str,
        trusted_device_id: uuid.UUID | None = None,
    ) -> AttendanceRiskSignal:
        """Triggered when challenge zone differs from final submission zone."""
        risk_key = f"ZONE_MIS:{university_id}:{user_id}:{session_id}:{submission_zone_code}"
        return await cls.record_risk_signal(
            db=db,
            university_id=university_id,
            signal_type=RiskSignalType.STUDENT_NETWORK_ZONE_MISMATCH.value,
            severity=RiskSeverity.MEDIUM.value,
            risk_points=25,
            subject_type=RiskSubjectType.STUDENT.value,
            risk_key=risk_key,
            subject_user_id=user_id,
            trusted_device_id=trusted_device_id,
            attendance_session_id=session_id,
            class_occurrence_id=occurrence_id,
            context={
                "rule": "STUDENT_NETWORK_ZONE_MISMATCH",
                "challenge_zone": challenge_zone_code,
                "submission_zone": submission_zone_code,
                "reason": "Challenge network zone does not match submission network zone.",
            },
        )

    @classmethod
    async def record_replay_attempt_signal(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        challenge_id: uuid.UUID,
        proof_id: uuid.UUID,
        trusted_device_id: uuid.UUID | None = None,
    ) -> AttendanceRiskSignal:
        """Triggered when an already-consumed challenge is replayed with another proof."""
        risk_key = f"NET_REPLAY:{university_id}:{user_id}:{challenge_id}:{proof_id}"
        return await cls.record_risk_signal(
            db=db,
            university_id=university_id,
            signal_type=RiskSignalType.NETWORK_PROOF_REPLAY_ATTEMPT.value,
            severity=RiskSeverity.HIGH.value,
            risk_points=50,
            subject_type=RiskSubjectType.DEVICE.value,
            risk_key=risk_key,
            subject_user_id=user_id,
            trusted_device_id=trusted_device_id,
            attendance_session_id=session_id,
            context={
                "rule": "NETWORK_PROOF_REPLAY_ATTEMPT",
                "challenge_id": str(challenge_id),
                "proof_id": str(proof_id),
                "reason": "Attempted to reuse an already consumed network presence challenge.",
            },
        )

    @classmethod
    async def record_header_spoof_signal(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        user_id: uuid.UUID | None,
        direct_peer: str,
        spoofed_header: str,
    ) -> AttendanceRiskSignal:
        """Triggered when an untrusted peer injects campus IPs in forwarding headers."""
        risk_key = f"HDR_SPOOF:{university_id}:{direct_peer}:{hash(spoofed_header)}"
        return await cls.record_risk_signal(
            db=db,
            university_id=university_id,
            signal_type=RiskSignalType.NETWORK_FORWARD_HEADER_SPOOF_ATTEMPT.value,
            severity=RiskSeverity.MEDIUM.value,
            risk_points=30,
            subject_type=RiskSubjectType.STUDENT.value if user_id else RiskSubjectType.DEVICE.value,
            risk_key=risk_key,
            subject_user_id=user_id,
            context={
                "rule": "NETWORK_FORWARD_HEADER_SPOOF_ATTEMPT",
                "direct_peer": direct_peer,
                "spoofed_header": spoofed_header[:200],
                "reason": "Forwarded headers containing internal IPs received from untrusted peer.",
            },
        )

    @classmethod
    async def record_account_reuse_attempt_signal(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        user_id: uuid.UUID,
        candidate_fingerprint: str,
        existing_owner_id: uuid.UUID,
    ) -> AttendanceRiskSignal:
        """Triggered when account attempts to register key bound to another account."""
        risk_key = f"ACC_REUSE:{university_id}:{user_id}:{candidate_fingerprint}"
        return await cls.record_risk_signal(
            db=db,
            university_id=university_id,
            signal_type=RiskSignalType.DEVICE_ACCOUNT_REUSE_ATTEMPT.value,
            severity=RiskSeverity.HIGH.value,
            risk_points=50,
            subject_type=RiskSubjectType.DEVICE.value,
            risk_key=risk_key,
            subject_user_id=user_id,
            context={
                "rule": "DEVICE_ACCOUNT_REUSE_ATTEMPT",
                "fingerprint": candidate_fingerprint,
                "existing_owner_user_id": str(existing_owner_id),
                "reason": "Attempted to register identity active on another account.",
            },
        )

    @classmethod
    async def record_lecturer_untrusted_network_signal(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        lecturer_user_id: uuid.UUID,
        session_id: uuid.UUID,
        client_ip: str,
    ) -> AttendanceRiskSignal:
        """Triggered when lecturer starts session from untrusted network in OPTIONAL mode."""
        risk_key = f"LEC_NET:{university_id}:{lecturer_user_id}:{session_id}"
        return await cls.record_risk_signal(
            db=db,
            university_id=university_id,
            signal_type=RiskSignalType.LECTURER_NETWORK_NOT_TRUSTED.value,
            severity=RiskSeverity.LOW.value,
            risk_points=15,
            subject_type=RiskSubjectType.LECTURER.value,
            risk_key=risk_key,
            subject_user_id=lecturer_user_id,
            attendance_session_id=session_id,
            context={
                "rule": "LECTURER_NETWORK_NOT_TRUSTED",
                "observed_ip": client_ip,
                "reason": "Lecturer initiated attendance from an untrusted campus network.",
            },
        )

    # =========================================================================
    # 3. Behavioral & Pattern Analysis Detectors
    # =========================================================================

    @classmethod
    async def analyze_device_replacement_frequency(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        student_id: uuid.UUID,
        user_id: uuid.UUID,
        current_time: datetime.datetime | None = None,
    ) -> AttendanceRiskSignal | None:
        """Detect rapid device replacement requests exceeding configured threshold."""
        now = current_time or utc_now()
        settings = get_settings()
        threshold = settings.ANTI_CHEAT_REPLACEMENT_THRESHOLD_COUNT
        window_days = settings.ANTI_CHEAT_REPLACEMENT_WINDOW_DAYS
        since_date = now - datetime.timedelta(days=window_days)

        count_stmt = select(func.count(DeviceReplacementRequest.id)).where(
            DeviceReplacementRequest.student_id == student_id,
            DeviceReplacementRequest.university_id == university_id,
            DeviceReplacementRequest.status == DeviceReplacementStatus.APPROVED.value,
            DeviceReplacementRequest.reviewed_at >= since_date,
        )
        c_res = await db.execute(count_stmt)
        count = c_res.scalar() or 0

        if count >= threshold:
            risk_key = f"DEV_FREQ:{university_id}:{student_id}:{now.strftime('%Y-%m')}"
            return await cls.record_risk_signal(
                db=db,
                university_id=university_id,
                signal_type=RiskSignalType.DEVICE_REPLACEMENT_FREQUENCY_HIGH.value,
                severity=RiskSeverity.MEDIUM.value,
                risk_points=30,
                subject_type=RiskSubjectType.STUDENT.value,
                risk_key=risk_key,
                subject_user_id=user_id,
                context={
                    "rule": "DEVICE_REPLACEMENT_FREQUENCY_HIGH",
                    "replacement_count": count,
                    "threshold": threshold,
                    "window_days": window_days,
                    "reason": (
                        f"Student has {count} approved device replacements in {window_days} days."
                    ),
                },
                current_time=now,
            )
        return None

    @classmethod
    async def analyze_overlapping_attendance(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        student_id: uuid.UUID,
        user_id: uuid.UUID,
        current_time: datetime.datetime | None = None,
    ) -> AttendanceRiskSignal | None:
        """Detect student credited with attendance for two overlapping class occurrences."""
        now = current_time or utc_now()
        # Query attendance records in PRESENT or LATE status for the student
        rec_stmt = (
            select(AttendanceRecord, ClassOccurrence)
            .join(AttendanceSession, AttendanceRecord.attendance_session_id == AttendanceSession.id)
            .join(ClassOccurrence, AttendanceSession.class_occurrence_id == ClassOccurrence.id)
            .where(
                AttendanceRecord.student_id == student_id,
                AttendanceSession.university_id == university_id,
                AttendanceRecord.status.in_(
                    [AttendanceStatus.PRESENT.value, AttendanceStatus.LATE.value]
                ),
            )
            .order_by(ClassOccurrence.scheduled_start_utc.asc())
        )
        res = await db.execute(rec_stmt)
        rows = res.all()

        for i in range(len(rows)):
            rec1, occ1 = rows[i]
            for j in range(i + 1, len(rows)):
                rec2, occ2 = rows[j]
                # Compare class occurrence schedules
                # Overlap if max(start1, start2) < min(end1, end2)
                overlap_start = max(occ1.scheduled_start_utc, occ2.scheduled_start_utc)
                overlap_end = min(occ1.scheduled_end_utc, occ2.scheduled_end_utc)
                if overlap_start < overlap_end:
                    risk_key = f"OVERLAP:{university_id}:{student_id}:{occ1.id}:{occ2.id}"
                    return await cls.record_risk_signal(
                        db=db,
                        university_id=university_id,
                        signal_type=RiskSignalType.STUDENT_OVERLAPPING_ATTENDANCE.value,
                        severity=RiskSeverity.HIGH.value,
                        risk_points=50,
                        subject_type=RiskSubjectType.STUDENT.value,
                        risk_key=risk_key,
                        subject_user_id=user_id,
                        attendance_session_id=rec1.attendance_session_id,
                        class_occurrence_id=occ1.id,
                        context={
                            "rule": "STUDENT_OVERLAPPING_ATTENDANCE",
                            "occurrence_1": str(occ1.id),
                            "occurrence_2": str(occ2.id),
                            "schedule_1": (
                                f"{occ1.scheduled_start_utc.isoformat()}-"
                                f"{occ1.scheduled_end_utc.isoformat()}"
                            ),
                            "schedule_2": (
                                f"{occ2.scheduled_start_utc.isoformat()}-"
                                f"{occ2.scheduled_end_utc.isoformat()}"
                            ),
                            "date": occ1.local_date.isoformat(),
                            "reason": (
                                "Student received attendance credit for overlapping scheduled"
                                " occurrences."
                            ),
                        },
                        current_time=now,
                    )
        return None

    @classmethod
    async def analyze_session_manual_attendance_rate(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> AttendanceRiskSignal | None:
        """Detect excessive manual override rate for an attendance session."""
        settings = get_settings()
        threshold_pct = settings.ANTI_CHEAT_MANUAL_RATE_THRESHOLD_PERCENT

        # Count total records vs manual records
        tot_stmt = select(func.count(AttendanceRecord.id)).where(
            AttendanceRecord.attendance_session_id == session_id
        )
        tot_res = await db.execute(tot_stmt)
        total_records = tot_res.scalar() or 0
        if total_records < 5:
            return None

        man_stmt = select(func.count(AttendanceRecord.id)).where(
            AttendanceRecord.attendance_session_id == session_id,
            AttendanceRecord.is_manual.is_(True),
        )
        man_res = await db.execute(man_stmt)
        manual_records = man_res.scalar() or 0

        rate = (manual_records / total_records) * 100.0
        if rate >= threshold_pct:
            risk_key = f"MAN_RATE:{university_id}:{session_id}"
            return await cls.record_risk_signal(
                db=db,
                university_id=university_id,
                signal_type=RiskSignalType.SESSION_MANUAL_ATTENDANCE_RATE_HIGH.value,
                severity=RiskSeverity.MEDIUM.value,
                risk_points=25,
                subject_type=RiskSubjectType.SESSION.value,
                risk_key=risk_key,
                attendance_session_id=session_id,
                context={
                    "rule": "SESSION_MANUAL_ATTENDANCE_RATE_HIGH",
                    "manual_records": manual_records,
                    "total_records": total_records,
                    "manual_percentage": round(rate, 2),
                    "threshold_percentage": threshold_pct,
                    "reason": (
                        f"{manual_records} of {total_records} records"
                        f" ({rate:.1f}%) were manually credited."
                    ),
                },
            )
        return None

    @classmethod
    async def analyze_mass_manual_attendance(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        session_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        manual_count: int,
    ) -> AttendanceRiskSignal | None:
        """Detect single-actor mass manual attendance override in a session."""
        settings = get_settings()
        threshold = settings.ANTI_CHEAT_MASS_MANUAL_COUNT_THRESHOLD
        if manual_count >= threshold:
            risk_key = f"MASS_MAN:{university_id}:{session_id}:{actor_user_id}"
            return await cls.record_risk_signal(
                db=db,
                university_id=university_id,
                signal_type=RiskSignalType.MASS_MANUAL_ATTENDANCE.value,
                severity=RiskSeverity.HIGH.value,
                risk_points=40,
                subject_type=RiskSubjectType.LECTURER.value,
                risk_key=risk_key,
                subject_user_id=actor_user_id,
                attendance_session_id=session_id,
                context={
                    "rule": "MASS_MANUAL_ATTENDANCE",
                    "actor_user_id": str(actor_user_id),
                    "manual_count": manual_count,
                    "threshold": threshold,
                    "reason": f"Actor manually credited {manual_count} students in this session.",
                },
            )
        return None

    @classmethod
    async def analyze_session_correction_rate(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> AttendanceRiskSignal | None:
        """Detect high post-session attendance revisions for a session."""
        settings = get_settings()
        threshold_pct = settings.ANTI_CHEAT_CORRECTION_RATE_THRESHOLD_PERCENT

        tot_stmt = select(func.count(AttendanceRecord.id)).where(
            AttendanceRecord.attendance_session_id == session_id
        )
        tot_res = await db.execute(tot_stmt)
        total_records = tot_res.scalar() or 0
        if total_records < 5:
            return None

        rev_stmt = select(func.count(AttendanceRevision.id)).where(
            AttendanceRevision.attendance_session_id == session_id
        )
        rev_res = await db.execute(rev_stmt)
        revision_count = rev_res.scalar() or 0

        rate = (revision_count / total_records) * 100.0
        if rate >= threshold_pct:
            risk_key = f"CORR_RATE:{university_id}:{session_id}"
            return await cls.record_risk_signal(
                db=db,
                university_id=university_id,
                signal_type=RiskSignalType.SESSION_CORRECTION_RATE_HIGH.value,
                severity=RiskSeverity.MEDIUM.value,
                risk_points=25,
                subject_type=RiskSubjectType.SESSION.value,
                risk_key=risk_key,
                attendance_session_id=session_id,
                context={
                    "rule": "SESSION_CORRECTION_RATE_HIGH",
                    "revision_count": revision_count,
                    "total_records": total_records,
                    "correction_percentage": round(rate, 2),
                    "threshold_percentage": threshold_pct,
                    "reason": (
                        f"{revision_count} attendance revisions"
                        f" ({rate:.1f}%) performed on this session."
                    ),
                },
            )
        return None

    @classmethod
    async def analyze_session_schedule_deviation(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        session_id: uuid.UUID,
        occurrence_id: uuid.UUID,
        scheduled_start: datetime.datetime,
        actual_start: datetime.datetime,
    ) -> AttendanceRiskSignal | None:
        """Detect attendance session activated substantially outside scheduled occurrence window."""
        settings = get_settings()
        threshold_min = settings.ANTI_CHEAT_SCHEDULE_DEVIATION_MINUTES

        diff_minutes = abs((actual_start - scheduled_start).total_seconds()) / 60.0
        if diff_minutes >= threshold_min:
            risk_key = f"SCHED_DEV:{university_id}:{session_id}"
            return await cls.record_risk_signal(
                db=db,
                university_id=university_id,
                signal_type=RiskSignalType.SESSION_OUTSIDE_SCHEDULE_WINDOW.value,
                severity=RiskSeverity.LOW.value,
                risk_points=10,
                subject_type=RiskSubjectType.SESSION.value,
                risk_key=risk_key,
                attendance_session_id=session_id,
                class_occurrence_id=occurrence_id,
                context={
                    "rule": "SESSION_OUTSIDE_SCHEDULE_WINDOW",
                    "scheduled_start": scheduled_start.isoformat(),
                    "actual_start": actual_start.isoformat(),
                    "deviation_minutes": round(diff_minutes, 1),
                    "threshold_minutes": threshold_min,
                    "reason": (
                        f"Session started {diff_minutes:.0f} minutes away"
                        " from scheduled occurrence."
                    ),
                },
            )
        return None

    # =========================================================================
    # 4. Staff Review Workflow
    # =========================================================================

    @staticmethod
    async def acknowledge_signal(
        db: AsyncSession,
        signal_id: uuid.UUID,
        university_id: uuid.UUID,
        reviewer_user_id: uuid.UUID,
        current_time: datetime.datetime | None = None,
    ) -> AttendanceRiskSignalResponse:
        """Acknowledge a risk signal by university administrator."""
        now = current_time or utc_now()
        stmt = select(AttendanceRiskSignal).where(
            AttendanceRiskSignal.id == signal_id,
            AttendanceRiskSignal.university_id == university_id,
        )
        res = await db.execute(stmt)
        signal = res.scalar_one_or_none()
        if not signal:
            raise NotFoundException("AttendanceRiskSignal", signal_id)

        signal.status = RiskSignalStatus.ACKNOWLEDGED.value
        signal.reviewed_at = now
        signal.reviewed_by_user_id = reviewer_user_id
        signal.updated_at = now
        await db.commit()
        await db.refresh(signal)
        return AttendanceRiskSignalResponse.model_validate(signal)

    @staticmethod
    async def resolve_signal(
        db: AsyncSession,
        signal_id: uuid.UUID,
        university_id: uuid.UUID,
        reviewer_user_id: uuid.UUID,
        review_note: str,
        current_time: datetime.datetime | None = None,
    ) -> AttendanceRiskSignalResponse:
        """Resolve a risk signal with mandatory justification note."""
        now = current_time or utc_now()
        stmt = select(AttendanceRiskSignal).where(
            AttendanceRiskSignal.id == signal_id,
            AttendanceRiskSignal.university_id == university_id,
        )
        res = await db.execute(stmt)
        signal = res.scalar_one_or_none()
        if not signal:
            raise NotFoundException("AttendanceRiskSignal", signal_id)

        signal.status = RiskSignalStatus.RESOLVED.value
        signal.reviewed_at = now
        signal.reviewed_by_user_id = reviewer_user_id
        signal.review_note = review_note.strip()
        signal.resolved_at = now
        signal.updated_at = now
        await db.commit()
        await db.refresh(signal)
        return AttendanceRiskSignalResponse.model_validate(signal)

    @staticmethod
    async def dismiss_signal(
        db: AsyncSession,
        signal_id: uuid.UUID,
        university_id: uuid.UUID,
        reviewer_user_id: uuid.UUID,
        review_note: str,
        current_time: datetime.datetime | None = None,
    ) -> AttendanceRiskSignalResponse:
        """Dismiss a false-positive risk signal with mandatory explanation."""
        now = current_time or utc_now()
        stmt = select(AttendanceRiskSignal).where(
            AttendanceRiskSignal.id == signal_id,
            AttendanceRiskSignal.university_id == university_id,
        )
        res = await db.execute(stmt)
        signal = res.scalar_one_or_none()
        if not signal:
            raise NotFoundException("AttendanceRiskSignal", signal_id)

        signal.status = RiskSignalStatus.DISMISSED.value
        signal.reviewed_at = now
        signal.reviewed_by_user_id = reviewer_user_id
        signal.review_note = review_note.strip()
        signal.updated_at = now
        await db.commit()
        await db.refresh(signal)
        return AttendanceRiskSignalResponse.model_validate(signal)

    @staticmethod
    async def list_risk_signals(
        db: AsyncSession,
        university_id: uuid.UUID,
        status: str | None = None,
        severity: str | None = None,
        signal_type: str | None = None,
        subject_user_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AttendanceRiskSignalResponse]:
        """List risk signals with filtering and pagination."""
        stmt = select(AttendanceRiskSignal).where(
            AttendanceRiskSignal.university_id == university_id
        )
        if status:
            stmt = stmt.where(AttendanceRiskSignal.status == status)
        if severity:
            stmt = stmt.where(AttendanceRiskSignal.severity == severity)
        if signal_type:
            stmt = stmt.where(AttendanceRiskSignal.signal_type == signal_type)
        if subject_user_id:
            stmt = stmt.where(AttendanceRiskSignal.subject_user_id == subject_user_id)
        if session_id:
            stmt = stmt.where(AttendanceRiskSignal.attendance_session_id == session_id)

        stmt = stmt.order_by(AttendanceRiskSignal.detected_at.desc()).limit(limit).offset(offset)
        res = await db.execute(stmt)
        return [AttendanceRiskSignalResponse.model_validate(s) for s in res.scalars().all()]

    @staticmethod
    async def get_risk_signal(
        db: AsyncSession,
        signal_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> AttendanceRiskSignalResponse:
        """Retrieve a specific risk signal by ID enforcing tenant isolation."""
        stmt = select(AttendanceRiskSignal).where(
            AttendanceRiskSignal.id == signal_id,
            AttendanceRiskSignal.university_id == university_id,
        )
        res = await db.execute(stmt)
        signal = res.scalar_one_or_none()
        if not signal:
            raise NotFoundException("AttendanceRiskSignal", signal_id)
        return AttendanceRiskSignalResponse.model_validate(signal)
