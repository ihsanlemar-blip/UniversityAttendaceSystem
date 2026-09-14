"""Attendance Service for lifecycle, policies, 3-checkpoint windows, and evaluation."""

import datetime
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.attendance.schemas import (
    AttendancePolicyCreateRequest,
    AttendancePolicyUpdateRequest,
)
from backend.app.common.types import utc_now
from backend.app.core.constants import (
    AttendanceAuditEventType,
    AttendanceCheckpointStatus,
    AttendanceCheckpointType,
    AttendanceSessionStatus,
    AttendanceStatus,
    ClassOccurrenceStatus,
    EnrollmentStatus,
    EvidenceSourceMode,
    PolicyScopeType,
    RecordStatus,
)
from backend.app.core.exceptions import ConflictException, DomainException, NotFoundException
from backend.app.models.academic_unit import AcademicUnit
from backend.app.models.attendance_checkpoint import AttendanceCheckpoint
from backend.app.models.attendance_evidence import AttendanceEvidence
from backend.app.models.attendance_policy import (
    DEFAULT_CHECKPOINT_WEIGHTS,
    DEFAULT_STATUS_CREDIT,
    DEFAULT_STATUS_MAPPING,
    AttendancePolicy,
)
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.attendance_revision import AttendanceRevision
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.class_occurrence import ClassOccurrence
from backend.app.models.course_offering import CourseOffering
from backend.app.models.enrollment import Enrollment
from backend.app.models.student import Student


class AttendanceService:
    """Core domain service for Attendance Policies, Sessions, Checkpoints, and Records."""

    # =========================================================================
    # 1. Attendance Policies
    # =========================================================================

    @staticmethod
    async def create_policy(
        db: AsyncSession,
        university_id: uuid.UUID,
        payload: AttendancePolicyCreateRequest,
    ) -> AttendancePolicy:
        """Create a new attendance policy with hierarchical scope definitions."""
        # Derive scope_id from academic_unit_id or course_id if not explicitly provided
        scope_id = payload.scope_id
        if scope_id is None:
            if payload.scope_type in (PolicyScopeType.FACULTY, PolicyScopeType.PROGRAM):
                scope_id = payload.academic_unit_id
            elif payload.scope_type == PolicyScopeType.COURSE:
                scope_id = payload.course_id

        policy = AttendancePolicy(
            university_id=university_id,
            academic_unit_id=payload.academic_unit_id,
            course_id=payload.course_id,
            name=payload.name,
            scope_type=payload.scope_type.value,
            scope_id=scope_id,
            min_attendance_percentage=payload.min_attendance_percentage,
            late_threshold_minutes=payload.late_threshold_minutes,
            lecturer_correction_window_hours=payload.lecturer_correction_window_hours,
            required_checkpoint_count=payload.required_checkpoint_count,
            checkpoint_duration_seconds=payload.checkpoint_duration_seconds,
            token_rotation_seconds=payload.token_rotation_seconds,
            checkpoint_weights=payload.checkpoint_weights,
            status_mapping=payload.status_mapping,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            status=RecordStatus.ACTIVE.value,
        )
        db.add(policy)
        await db.commit()
        await db.refresh(policy)
        return policy

    @staticmethod
    async def get_policy(
        db: AsyncSession,
        policy_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> AttendancePolicy:
        """Retrieve policy by ID ensuring tenant isolation."""
        stmt = select(AttendancePolicy).where(
            AttendancePolicy.id == policy_id,
            AttendancePolicy.university_id == university_id,
        )
        res = await db.execute(stmt)
        policy = res.scalar_one_or_none()
        if not policy:
            raise NotFoundException("AttendancePolicy", policy_id)
        return policy

    @staticmethod
    async def update_policy(
        db: AsyncSession,
        policy_id: uuid.UUID,
        university_id: uuid.UUID,
        payload: AttendancePolicyUpdateRequest,
    ) -> AttendancePolicy:
        """Update configurable parameters of an attendance policy."""
        policy = await AttendanceService.get_policy(db, policy_id, university_id)
        update_data = payload.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(policy, field):
                if isinstance(value, RecordStatus):
                    setattr(policy, field, value.value)
                else:
                    setattr(policy, field, value)

        await db.commit()
        await db.refresh(policy)
        return policy

    @staticmethod
    async def list_policies(
        db: AsyncSession,
        university_id: uuid.UUID,
        scope_type: str | None = None,
        status: str | None = None,
    ) -> list[AttendancePolicy]:
        """List attendance policies matching scope filters."""
        stmt = select(AttendancePolicy).where(AttendancePolicy.university_id == university_id)
        if scope_type:
            stmt = stmt.where(AttendancePolicy.scope_type == scope_type)
        if status:
            stmt = stmt.where(AttendancePolicy.status == status)
        stmt = stmt.order_by(AttendancePolicy.name)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def resolve_policy_for_occurrence(
        db: AsyncSession,
        occurrence_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> tuple[AttendancePolicy | None, dict[str, Any]]:
        """Hierarchical policy resolution for a concrete class occurrence:

        Course override -> Program override -> Faculty override ->
        University default -> System fallback.
        Returns a tuple of (resolved_policy_or_none, policy_snapshot_dict).
        """
        stmt = (
            select(ClassOccurrence)
            .options(
                selectinload(ClassOccurrence.course_offering).selectinload(CourseOffering.course),
            )
            .where(
                ClassOccurrence.id == occurrence_id,
                ClassOccurrence.university_id == university_id,
            )
        )
        res = await db.execute(stmt)
        occurrence = res.scalar_one_or_none()
        if not occurrence or not occurrence.course_offering:
            raise NotFoundException("ClassOccurrence", occurrence_id)

        offering = occurrence.course_offering
        course = offering.course

        # 1. Course Override
        if course:
            course_stmt = (
                select(AttendancePolicy)
                .where(
                    AttendancePolicy.university_id == university_id,
                    AttendancePolicy.scope_type == PolicyScopeType.COURSE.value,
                    AttendancePolicy.course_id == course.id,
                    AttendancePolicy.status == RecordStatus.ACTIVE.value,
                )
                .order_by(AttendancePolicy.created_at.desc())
            )
            course_res = await db.execute(course_stmt)
            course_policy = course_res.scalars().first()
            if course_policy:
                return course_policy, AttendanceService._create_policy_snapshot(course_policy)

        # 2. Program / Department Override
        unit_id = offering.academic_unit_id or (course.academic_unit_id if course else None)
        curr_unit_id = unit_id
        while curr_unit_id:
            unit_stmt = (
                select(AttendancePolicy)
                .where(
                    AttendancePolicy.university_id == university_id,
                    AttendancePolicy.scope_id == curr_unit_id,
                    AttendancePolicy.status == RecordStatus.ACTIVE.value,
                )
                .order_by(AttendancePolicy.created_at.desc())
            )
            unit_res = await db.execute(unit_stmt)
            unit_policy = unit_res.scalars().first()
            if unit_policy:
                return unit_policy, AttendanceService._create_policy_snapshot(unit_policy)

            # Traverse parent unit
            unit = await db.get(AcademicUnit, curr_unit_id)
            curr_unit_id = unit.parent_id if unit else None

        # 3. University Default
        uni_stmt = (
            select(AttendancePolicy)
            .where(
                AttendancePolicy.university_id == university_id,
                AttendancePolicy.scope_type == PolicyScopeType.UNIVERSITY.value,
                AttendancePolicy.status == RecordStatus.ACTIVE.value,
            )
            .order_by(AttendancePolicy.created_at.desc())
        )
        uni_res = await db.execute(uni_stmt)
        uni_policy = uni_res.scalars().first()
        if uni_policy:
            return uni_policy, AttendanceService._create_policy_snapshot(uni_policy)

        # 4. Fallback Default
        fallback_snapshot = {
            "name": "System Institutional Fallback",
            "scope_type": "UNIVERSITY",
            "min_attendance_percentage": 75.0,
            "late_threshold_minutes": 10,
            "lecturer_correction_window_hours": 24,
            "required_checkpoint_count": 3,
            "checkpoint_duration_seconds": 300,
            "token_rotation_seconds": 30,
            "checkpoint_weights": dict(DEFAULT_CHECKPOINT_WEIGHTS),
            "status_mapping": dict(DEFAULT_STATUS_MAPPING),
            "status_credit": dict(DEFAULT_STATUS_CREDIT),
        }
        return None, fallback_snapshot

    @staticmethod
    def _create_policy_snapshot(policy: AttendancePolicy) -> dict[str, Any]:
        """Create an immutable snapshot dictionary of an attendance policy."""
        return {
            "policy_id": str(policy.id),
            "name": policy.name,
            "scope_type": policy.scope_type,
            "min_attendance_percentage": float(policy.min_attendance_percentage),
            "late_threshold_minutes": policy.late_threshold_minutes,
            "lecturer_correction_window_hours": policy.lecturer_correction_window_hours,
            "required_checkpoint_count": policy.required_checkpoint_count,
            "checkpoint_duration_seconds": policy.checkpoint_duration_seconds,
            "token_rotation_seconds": policy.token_rotation_seconds,
            "checkpoint_weights": dict(policy.checkpoint_weights),
            "status_mapping": dict(policy.status_mapping),
            "status_credit": dict(DEFAULT_STATUS_CREDIT),
        }

    # =========================================================================
    # 2. Attendance Sessions & Frozen Roster
    # =========================================================================

    @staticmethod
    async def initialize_session(
        db: AsyncSession,
        university_id: uuid.UUID,
        class_occurrence_id: uuid.UUID,
        actor_id: uuid.UUID,
        attendance_policy_id: uuid.UUID | None = None,
        activate_immediately: bool = False,
    ) -> AttendanceSession:
        """Initialize an AttendanceSession anchored 1:1 to a ClassOccurrence."""
        # Validate occurrence
        stmt = (
            select(ClassOccurrence)
            .options(
                selectinload(ClassOccurrence.course_offering),
            )
            .where(
                ClassOccurrence.id == class_occurrence_id,
                ClassOccurrence.university_id == university_id,
            )
        )
        res = await db.execute(stmt)
        occurrence = res.scalar_one_or_none()
        if not occurrence:
            raise NotFoundException("ClassOccurrence", class_occurrence_id)

        # Invariant checks
        if occurrence.status == ClassOccurrenceStatus.CANCELLED.value:
            raise DomainException(
                code="OCCURRENCE_CANCELLED",
                message="Cannot initialize attendance session for a cancelled class occurrence.",
                status_code=400,
            )
        if occurrence.rescheduled_to_id is not None:
            raise DomainException(
                code="OCCURRENCE_SUPERSEDED",
                message="Cannot initialize attendance session for a rescheduled class occurrence.",
                status_code=400,
            )

        # Unique 1:1 check
        sess_check = select(AttendanceSession).where(
            AttendanceSession.class_occurrence_id == class_occurrence_id
        )
        existing_sess = (await db.execute(sess_check)).scalar_one_or_none()
        if existing_sess:
            raise ConflictException(
                "An attendance session already exists for this class occurrence."
            )

        # Policy resolution
        if attendance_policy_id:
            policy = await AttendanceService.get_policy(db, attendance_policy_id, university_id)
            policy_snapshot = AttendanceService._create_policy_snapshot(policy)
            resolved_policy_id: uuid.UUID | None = policy.id
        else:
            policy_obj, policy_snapshot = await AttendanceService.resolve_policy_for_occurrence(
                db=db,
                occurrence_id=class_occurrence_id,
                university_id=university_id,
            )
            resolved_policy_id = policy_obj.id if policy_obj else None

        initial_status = (
            AttendanceSessionStatus.ACTIVE.value
            if activate_immediately
            else AttendanceSessionStatus.SCHEDULED.value
        )
        now = utc_now()

        session = AttendanceSession(
            university_id=university_id,
            class_occurrence_id=class_occurrence_id,
            attendance_policy_id=resolved_policy_id,
            policy_snapshot=policy_snapshot,
            status=initial_status,
            opened_at_utc=now if activate_immediately else None,
            opened_by_user_id=actor_id if activate_immediately else None,
        )
        db.add(session)
        await db.flush()

        # Pre-create the approved 3 checkpoints (START, MIDDLE, END)
        duration = policy_snapshot.get("checkpoint_duration_seconds", 300)
        checkpoints = [
            AttendanceCheckpoint(
                attendance_session_id=session.id,
                checkpoint_type=AttendanceCheckpointType.START.value,
                sequence_no=1,
                status=AttendanceCheckpointStatus.SCHEDULED.value,
                window_duration_seconds=duration,
            ),
            AttendanceCheckpoint(
                attendance_session_id=session.id,
                checkpoint_type=AttendanceCheckpointType.MIDDLE.value,
                sequence_no=2,
                status=AttendanceCheckpointStatus.SCHEDULED.value,
                window_duration_seconds=duration,
            ),
            AttendanceCheckpoint(
                attendance_session_id=session.id,
                checkpoint_type=AttendanceCheckpointType.END.value,
                sequence_no=3,
                status=AttendanceCheckpointStatus.SCHEDULED.value,
                window_duration_seconds=duration,
            ),
        ]
        db.add_all(checkpoints)

        # If activated immediately, freeze active roster
        if activate_immediately:
            await AttendanceService._freeze_roster(db, session, occurrence.course_offering_id)

        # Audit revision log
        audit_event = AttendanceRevision(
            attendance_session_id=session.id,
            attendance_record_id=None,
            actor_user_id=actor_id,
            event_type=AttendanceAuditEventType.SESSION_INITIALIZED.value,
            previous_status=None,
            new_status=session.status,
            reason="Attendance session initialized.",
            occurred_at_utc=now,
        )
        db.add(audit_event)

        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def _freeze_roster(
        db: AsyncSession,
        session: AttendanceSession,
        course_offering_id: uuid.UUID,
    ) -> int:
        """Freeze active enrollment roster into AttendanceRecord rows in PENDING status.

        Guarantees that subsequent student drops or adds do not retroactively alter the
        frozen class attendance sheet.
        """
        # Query active enrollments
        stmt = select(Enrollment.student_id).where(
            Enrollment.course_offering_id == course_offering_id,
            Enrollment.status == EnrollmentStatus.ACTIVE.value,
        )
        res = await db.execute(stmt)
        active_student_ids = list(res.scalars().all())

        # Check existing records to prevent duplicates
        existing_stmt = select(AttendanceRecord.student_id).where(
            AttendanceRecord.attendance_session_id == session.id
        )
        existing_res = await db.execute(existing_stmt)
        existing_student_ids = set(existing_res.scalars().all())

        new_records = []
        for s_id in active_student_ids:
            if s_id not in existing_student_ids:
                new_records.append(
                    AttendanceRecord(
                        attendance_session_id=session.id,
                        student_id=s_id,
                        status=AttendanceStatus.PENDING.value,
                        start_credited=False,
                        middle_credited=False,
                        end_credited=False,
                        checkpoints_verified=0,
                        attendance_credit=0.0,
                    )
                )

        if new_records:
            db.add_all(new_records)
            await db.flush()

        return len(new_records)

    @staticmethod
    async def open_session(
        db: AsyncSession,
        session_id: uuid.UUID,
        university_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> AttendanceSession:
        """Activate a scheduled or paused attendance session and freeze active roster."""
        session = await AttendanceService.get_session(db, session_id, university_id)

        if session.status == AttendanceSessionStatus.CLOSED.value:
            raise DomainException(
                code="SESSION_ALREADY_CLOSED",
                message="Cannot reopen a closed attendance session.",
                status_code=400,
            )

        if session.status == AttendanceSessionStatus.ACTIVE.value:
            return session  # Idempotent

        now = utc_now()
        prev_status = session.status
        session.status = AttendanceSessionStatus.ACTIVE.value
        if session.opened_at_utc is None:
            session.opened_at_utc = now
            session.opened_by_user_id = actor_id

        # Freeze roster if not already frozen
        occ = await db.get(ClassOccurrence, session.class_occurrence_id)
        if occ:
            await AttendanceService._freeze_roster(db, session, occ.course_offering_id)

        # Audit revision log
        db.add(
            AttendanceRevision(
                attendance_session_id=session.id,
                attendance_record_id=None,
                actor_user_id=actor_id,
                event_type=AttendanceAuditEventType.SESSION_OPENED.value,
                previous_status=prev_status,
                new_status=session.status,
                reason="Attendance session activated.",
                occurred_at_utc=now,
            )
        )

        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def pause_session(
        db: AsyncSession,
        session_id: uuid.UUID,
        university_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> AttendanceSession:
        """Pause an active attendance session and close any currently open checkpoint."""
        session = await AttendanceService.get_session(db, session_id, university_id)
        if session.status != AttendanceSessionStatus.ACTIVE.value:
            raise DomainException(
                code="INVALID_STATE",
                message="Only active sessions can be paused.",
                status_code=400,
            )

        now = utc_now()
        session.status = AttendanceSessionStatus.PAUSED.value
        session.paused_at_utc = now

        # Close any open checkpoint
        cp_stmt = select(AttendanceCheckpoint).where(
            AttendanceCheckpoint.attendance_session_id == session.id,
            AttendanceCheckpoint.status == AttendanceCheckpointStatus.OPEN.value,
        )
        res = await db.execute(cp_stmt)
        open_cps = res.scalars().all()
        for cp in open_cps:
            cp.status = AttendanceCheckpointStatus.CLOSED.value
            cp.closed_at_utc = now
            cp.closed_by_user_id = actor_id

        db.add(
            AttendanceRevision(
                attendance_session_id=session.id,
                attendance_record_id=None,
                actor_user_id=actor_id,
                event_type=AttendanceAuditEventType.SESSION_PAUSED.value,
                previous_status=AttendanceSessionStatus.ACTIVE.value,
                new_status=session.status,
                reason="Attendance session paused.",
                occurred_at_utc=now,
            )
        )

        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def resume_session(
        db: AsyncSession,
        session_id: uuid.UUID,
        university_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> AttendanceSession:
        """Resume a paused attendance session."""
        session = await AttendanceService.get_session(db, session_id, university_id)
        if session.status != AttendanceSessionStatus.PAUSED.value:
            raise DomainException(
                code="INVALID_STATE",
                message="Only paused sessions can be resumed.",
                status_code=400,
            )

        now = utc_now()
        session.status = AttendanceSessionStatus.ACTIVE.value
        session.resumed_at_utc = now

        db.add(
            AttendanceRevision(
                attendance_session_id=session.id,
                attendance_record_id=None,
                actor_user_id=actor_id,
                event_type=AttendanceAuditEventType.SESSION_RESUMED.value,
                previous_status=AttendanceSessionStatus.PAUSED.value,
                new_status=session.status,
                reason="Attendance session resumed.",
                occurred_at_utc=now,
            )
        )

        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def close_session(
        db: AsyncSession,
        session_id: uuid.UUID,
        university_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> AttendanceSession:
        """Close an attendance session and evaluate final status for all student records."""
        session = await AttendanceService.get_session(db, session_id, university_id)
        if session.status == AttendanceSessionStatus.CLOSED.value:
            return session  # Idempotent

        now = utc_now()
        prev_status = session.status
        session.status = AttendanceSessionStatus.CLOSED.value
        session.closed_at_utc = now
        session.closed_by_user_id = actor_id

        # Close any open checkpoint
        cp_stmt = select(AttendanceCheckpoint).where(
            AttendanceCheckpoint.attendance_session_id == session.id,
            AttendanceCheckpoint.status == AttendanceCheckpointStatus.OPEN.value,
        )
        res = await db.execute(cp_stmt)
        for cp in res.scalars().all():
            cp.status = AttendanceCheckpointStatus.CLOSED.value
            cp.closed_at_utc = now
            cp.closed_by_user_id = actor_id

        # Combinatorial 8-pattern evaluation of all student records in session
        await AttendanceService._evaluate_session_records(db, session, now)

        db.add(
            AttendanceRevision(
                attendance_session_id=session.id,
                attendance_record_id=None,
                actor_user_id=actor_id,
                event_type=AttendanceAuditEventType.SESSION_CLOSED.value,
                previous_status=prev_status,
                new_status=session.status,
                reason="Attendance session closed and attendance evaluated.",
                occurred_at_utc=now,
            )
        )

        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_session(
        db: AsyncSession,
        session_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> AttendanceSession:
        """Retrieve AttendanceSession by ID with tenant check."""
        stmt = (
            select(AttendanceSession)
            .options(
                selectinload(AttendanceSession.checkpoints),
            )
            .where(
                AttendanceSession.id == session_id,
                AttendanceSession.university_id == university_id,
            )
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise NotFoundException("AttendanceSession", session_id)
        return session

    @staticmethod
    async def get_session_by_occurrence(
        db: AsyncSession,
        occurrence_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> AttendanceSession | None:
        """Retrieve AttendanceSession anchored to a ClassOccurrence."""
        stmt = (
            select(AttendanceSession)
            .options(
                selectinload(AttendanceSession.checkpoints),
            )
            .where(
                AttendanceSession.class_occurrence_id == occurrence_id,
                AttendanceSession.university_id == university_id,
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    # =========================================================================
    # 3. Attendance Checkpoints
    # =========================================================================

    @staticmethod
    async def open_checkpoint(
        db: AsyncSession,
        session_id: uuid.UUID,
        checkpoint_type: str,
        university_id: uuid.UUID,
        actor_id: uuid.UUID,
        window_duration_seconds: int | None = None,
    ) -> AttendanceCheckpoint:
        """Open an attendance checkpoint window (START, MIDDLE, or END)."""
        session = await AttendanceService.get_session(db, session_id, university_id)
        if session.status != AttendanceSessionStatus.ACTIVE.value:
            raise DomainException(
                code="SESSION_NOT_ACTIVE",
                message="Cannot open checkpoint when attendance session is not active.",
                status_code=400,
            )

        if checkpoint_type not in (
            AttendanceCheckpointType.START.value,
            AttendanceCheckpointType.MIDDLE.value,
            AttendanceCheckpointType.END.value,
        ):
            raise DomainException(
                code="INVALID_CHECKPOINT_TYPE",
                message=(
                    f"Invalid checkpoint type '{checkpoint_type}'. Must be START, MIDDLE, or END."
                ),
                status_code=400,
            )

        # Enforce sequential integrity: No two checkpoints may be open concurrently
        for cp in session.checkpoints:
            if (
                cp.status == AttendanceCheckpointStatus.OPEN.value
                and cp.checkpoint_type != checkpoint_type
            ):
                raise DomainException(
                    code="CHECKPOINT_ALREADY_OPEN",
                    message=f"Checkpoint '{cp.checkpoint_type}' is already open in this session.",
                    status_code=400,
                )

        # Find requested checkpoint
        target_cp = next(
            (cp for cp in session.checkpoints if cp.checkpoint_type == checkpoint_type),
            None,
        )
        if not target_cp:
            raise NotFoundException("AttendanceCheckpoint", checkpoint_type)

        if target_cp.status == AttendanceCheckpointStatus.OPEN.value:
            return target_cp  # Idempotent

        if target_cp.status == AttendanceCheckpointStatus.CLOSED.value:
            raise DomainException(
                code="CHECKPOINT_ALREADY_CLOSED",
                message=f"Checkpoint '{checkpoint_type}' window has already concluded.",
                status_code=400,
            )

        now = utc_now()
        target_cp.status = AttendanceCheckpointStatus.OPEN.value
        target_cp.opened_at_utc = now
        target_cp.opened_by_user_id = actor_id
        if window_duration_seconds is not None:
            target_cp.window_duration_seconds = window_duration_seconds

        db.add(
            AttendanceRevision(
                attendance_session_id=session.id,
                attendance_record_id=None,
                actor_user_id=actor_id,
                event_type=AttendanceAuditEventType.CHECKPOINT_OPENED.value,
                previous_status=AttendanceCheckpointStatus.SCHEDULED.value,
                new_status=target_cp.status,
                reason=f"Checkpoint {checkpoint_type} opened.",
                occurred_at_utc=now,
            )
        )

        await db.commit()
        await db.refresh(target_cp)
        return target_cp

    @staticmethod
    async def close_checkpoint(
        db: AsyncSession,
        session_id: uuid.UUID,
        checkpoint_type: str,
        university_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> AttendanceCheckpoint:
        """Close an open attendance checkpoint window."""
        session = await AttendanceService.get_session(db, session_id, university_id)
        target_cp = next(
            (cp for cp in session.checkpoints if cp.checkpoint_type == checkpoint_type),
            None,
        )
        if not target_cp:
            raise NotFoundException("AttendanceCheckpoint", checkpoint_type)

        if target_cp.status == AttendanceCheckpointStatus.CLOSED.value:
            return target_cp  # Idempotent

        if target_cp.status != AttendanceCheckpointStatus.OPEN.value:
            raise DomainException(
                code="CHECKPOINT_NOT_OPEN",
                message=f"Checkpoint '{checkpoint_type}' is not currently open.",
                status_code=400,
            )

        now = utc_now()
        target_cp.status = AttendanceCheckpointStatus.CLOSED.value
        target_cp.closed_at_utc = now
        target_cp.closed_by_user_id = actor_id

        db.add(
            AttendanceRevision(
                attendance_session_id=session.id,
                attendance_record_id=None,
                actor_user_id=actor_id,
                event_type=AttendanceAuditEventType.CHECKPOINT_CLOSED.value,
                previous_status=AttendanceCheckpointStatus.OPEN.value,
                new_status=target_cp.status,
                reason=f"Checkpoint {checkpoint_type} closed.",
                occurred_at_utc=now,
            )
        )

        await db.commit()
        await db.refresh(target_cp)
        return target_cp

    # =========================================================================
    # 4. Checkpoint Credit & Evidence Verification (INV-01, INV-05)
    # =========================================================================

    @staticmethod
    async def record_verified_checkpoint_credit(
        db: AsyncSession,
        session_id: uuid.UUID,
        checkpoint_type: str,
        student_id: uuid.UUID,
        actor_id: uuid.UUID,
        source_mode: str = EvidenceSourceMode.MANUAL.value,
        reason: str | None = None,
        evidence_metadata: dict[str, Any] | None = None,
        request_id: str | None = None,
        is_real_time: bool = True,
        override_now: datetime.datetime | None = None,
    ) -> AttendanceEvidence:
        """Trusted server service that records verified attendance evidence and credits checkpoint.

        Enforces:
        - INV-01: Client cannot mark itself present. Only trusted verification grants credit.
        - INV-05: Exactly one credit per student per checkpoint in a session.
        - Server UTC clock authority: Checks window expiration against authoritative time.
        """
        now = override_now or utc_now()

        # 1. Fetch checkpoint
        stmt = (
            select(AttendanceCheckpoint)
            .join(
                AttendanceSession,
                AttendanceSession.id == AttendanceCheckpoint.attendance_session_id,
            )
            .options(selectinload(AttendanceCheckpoint.session))
            .where(
                AttendanceCheckpoint.attendance_session_id == session_id,
                AttendanceCheckpoint.checkpoint_type == checkpoint_type,
            )
        )
        res = await db.execute(stmt)
        cp = res.scalar_one_or_none()
        if not cp:
            raise NotFoundException("AttendanceCheckpoint", checkpoint_type)

        session = cp.session

        # 2. Check window and status
        if is_real_time:
            if session.status != AttendanceSessionStatus.ACTIVE.value:
                raise DomainException(
                    code="SESSION_NOT_ACTIVE",
                    message="Cannot submit verification when session is not active.",
                    status_code=400,
                )
            if cp.status != AttendanceCheckpointStatus.OPEN.value:
                raise DomainException(
                    code="CHECKPOINT_NOT_OPEN",
                    message=f"Checkpoint '{checkpoint_type}' is not currently open.",
                    status_code=400,
                )

            # Check window expiration against server UTC clock
            if cp.opened_at_utc is not None:
                elapsed_seconds = (now - cp.opened_at_utc).total_seconds()
                if elapsed_seconds > cp.window_duration_seconds:
                    # Auto-close expired checkpoint
                    cp.status = AttendanceCheckpointStatus.CLOSED.value
                    cp.closed_at_utc = now
                    diff_sec = int(elapsed_seconds - cp.window_duration_seconds)
                    raise DomainException(
                        code="CHECKPOINT_WINDOW_EXPIRED",
                        message=f"Checkpoint window expired {diff_sec}s ago.",
                        status_code=400,
                    )

        # 3. Find student record in frozen roster
        rec_stmt = select(AttendanceRecord).where(
            AttendanceRecord.attendance_session_id == session_id,
            AttendanceRecord.student_id == student_id,
        )
        rec_res = await db.execute(rec_stmt)
        record = rec_res.scalar_one_or_none()
        if not record:
            raise DomainException(
                code="STUDENT_NOT_ROSTERED",
                message="Student is not part of this class session's attendance roster.",
                status_code=400,
            )

        # 4. Duplicate Check (INV-05)
        ev_stmt = select(AttendanceEvidence).where(
            AttendanceEvidence.attendance_checkpoint_id == cp.id,
            AttendanceEvidence.student_id == student_id,
        )
        ev_res = await db.execute(ev_stmt)
        existing_evidence = ev_res.scalar_one_or_none()
        if existing_evidence:
            # Idempotent response: student already credited for this checkpoint
            return existing_evidence

        # 5. Create AttendanceEvidence record
        evidence = AttendanceEvidence(
            attendance_checkpoint_id=cp.id,
            student_id=student_id,
            submitted_by_user_id=actor_id,
            source_mode=source_mode,
            server_received_at_utc=now,
            manual_reason=reason,
            evidence_metadata=evidence_metadata,
            request_id=request_id,
            created_at=now,
        )
        db.add(evidence)

        # 6. Credit AttendanceRecord
        if checkpoint_type == AttendanceCheckpointType.START.value:
            record.start_credited = True
        elif checkpoint_type == AttendanceCheckpointType.MIDDLE.value:
            record.middle_credited = True
        elif checkpoint_type == AttendanceCheckpointType.END.value:
            record.end_credited = True

        record.checkpoints_verified = sum(
            [
                record.start_credited,
                record.middle_credited,
                record.end_credited,
            ]
        )

        # Audit revision log
        event_name = (
            AttendanceAuditEventType.MANUAL_CHECKPOINT_CREDIT.value
            if source_mode == EvidenceSourceMode.MANUAL.value
            else AttendanceAuditEventType.CHECKPOINT_CREDITED.value
        )
        db.add(
            AttendanceRevision(
                attendance_session_id=session_id,
                attendance_record_id=record.id,
                actor_user_id=actor_id,
                event_type=event_name,
                previous_status=record.status,
                new_status=record.status,
                reason=reason or f"Checkpoint {checkpoint_type} credited via {source_mode}.",
                occurred_at_utc=now,
            )
        )

        await db.commit()
        await db.refresh(evidence)
        return evidence

    # =========================================================================
    # 5. Combinatorial 8-Pattern Evaluation Engine
    # =========================================================================

    @staticmethod
    async def _evaluate_session_records(
        db: AsyncSession,
        session: AttendanceSession,
        now: datetime.datetime,
    ) -> None:
        """Evaluate all student records for a session against frozen policy status mapping."""
        stmt = select(AttendanceRecord).where(AttendanceRecord.attendance_session_id == session.id)
        res = await db.execute(stmt)
        records = res.scalars().all()

        status_mapping = session.policy_snapshot.get("status_mapping", DEFAULT_STATUS_MAPPING)

        for record in records:
            # Preserve administrative EXCUSED or LEAVE overrides
            if record.status in (AttendanceStatus.EXCUSED.value, AttendanceStatus.LEAVE.value):
                continue

            # Calculate 3-bit pattern
            pattern = (
                f"{int(record.start_credited)}"
                f"{int(record.middle_credited)}"
                f"{int(record.end_credited)}"
            )

            # Lookup target status
            target_status = status_mapping.get(pattern, AttendanceStatus.ABSENT.value)
            record.status = target_status

            # Calculate credit value
            if target_status == AttendanceStatus.PRESENT.value:
                record.attendance_credit = 1.0
            elif target_status == AttendanceStatus.LATE.value:
                # 0.5 or 0.75 partial credit for late
                record.attendance_credit = 0.5
            else:
                record.attendance_credit = 0.0

            record.calculation_snapshot = {
                "pattern": pattern,
                "start": record.start_credited,
                "middle": record.middle_credited,
                "end": record.end_credited,
                "evaluated_at": now.isoformat(),
                "policy_snapshot": session.policy_snapshot,
            }
            record.finalized_at_utc = now

    # =========================================================================
    # 6. Manual Overrides & Revisions Ledger (INV-06, INV-08)
    # =========================================================================

    @staticmethod
    async def override_record_status(
        db: AsyncSession,
        record_id: uuid.UUID,
        actor_id: uuid.UUID,
        target_status: AttendanceStatus,
        reason: str,
        new_credit: float | None = None,
    ) -> AttendanceRecord:
        """Manual attendance status override by lecturer or administrator (INV-06, INV-08).

        Enforces:
        - Mandatory non-empty reason
        - Historical immutability (original record audit trail preserved)
        - Append-only revision ledger entry
        """
        if not reason or len(reason.strip()) < 3:
            raise DomainException(
                code="REASON_REQUIRED",
                message="A non-empty justification is mandatory for manual attendance overrides.",
                status_code=400,
            )

        stmt = select(AttendanceRecord).where(AttendanceRecord.id == record_id)
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            raise NotFoundException("AttendanceRecord", record_id)

        now = utc_now()
        prev_status = record.status
        prev_credit = float(record.attendance_credit)

        session = await db.get(AttendanceSession, record.attendance_session_id)
        policy_snapshot = session.policy_snapshot if session and session.policy_snapshot else {}
        status_credit_map: dict[str, Any] = policy_snapshot.get("status_credit", DEFAULT_STATUS_CREDIT)

        # Default credit calculation if not overridden
        calculated_credit = new_credit
        if calculated_credit is None:
            if target_status.value in status_credit_map:
                calculated_credit = float(status_credit_map[target_status.value])
            elif target_status == AttendanceStatus.PRESENT:
                calculated_credit = 1.0
            elif target_status == AttendanceStatus.LATE:
                calculated_credit = 0.5
            elif target_status == AttendanceStatus.EXCUSED:
                calculated_credit = float(policy_snapshot.get("excused_credit", 0.0))
            elif target_status == AttendanceStatus.LEAVE:
                calculated_credit = float(policy_snapshot.get("leave_credit", 0.0))
            else:
                calculated_credit = 0.0

        # Update record
        record.status = target_status.value
        record.attendance_credit = calculated_credit
        record.is_manual = True
        record.manual_reason = reason.strip()
        record.version_no += 1
        record.finalized_at_utc = now

        # Append-only revision entry (INV-06, INV-08)
        revision = AttendanceRevision(
            attendance_session_id=record.attendance_session_id,
            attendance_record_id=record.id,
            actor_user_id=actor_id,
            event_type=AttendanceAuditEventType.MANUAL_RECORD_OVERRIDE.value,
            previous_status=prev_status,
            new_status=record.status,
            previous_credit=prev_credit,
            new_credit=calculated_credit,
            reason=reason.strip(),
            occurred_at_utc=now,
        )
        db.add(revision)

        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def get_session_records(
        db: AsyncSession,
        session_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> list[AttendanceRecord]:
        """Fetch all roster attendance records for a session."""
        await AttendanceService.get_session(db, session_id, university_id)
        stmt = (
            select(AttendanceRecord)
            .options(selectinload(AttendanceRecord.student).selectinload(Student.user))
            .where(AttendanceRecord.attendance_session_id == session_id)
            .order_by(AttendanceRecord.created_at)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_student_attendance_history(
        db: AsyncSession,
        student_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Retrieve student's personal attendance history for self-view."""
        stmt = (
            select(AttendanceRecord)
            .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.attendance_session_id)
            .join(ClassOccurrence, ClassOccurrence.id == AttendanceSession.class_occurrence_id)
            .join(CourseOffering, CourseOffering.id == ClassOccurrence.course_offering_id)
            .options(
                selectinload(AttendanceRecord.session)
                .selectinload(AttendanceSession.class_occurrence)
                .selectinload(ClassOccurrence.course_offering)
                .selectinload(CourseOffering.course),
            )
            .where(AttendanceRecord.student_id == student_id)
            .order_by(ClassOccurrence.scheduled_start_utc.desc())
        )
        res = await db.execute(stmt)
        records = res.scalars().all()

        results = []
        for r in records:
            sess = r.session
            occ = sess.class_occurrence
            offering = occ.course_offering
            course = offering.course
            results.append(
                {
                    "record_id": r.id,
                    "session_id": sess.id,
                    "class_occurrence_id": occ.id,
                    "course_code": course.code if course else "UNKNOWN",
                    "course_name": course.name if course else "Unknown Course",
                    "occurrence_date": occ.local_date,
                    "scheduled_start_utc": occ.scheduled_start_utc,
                    "scheduled_end_utc": occ.scheduled_end_utc,
                    "status": r.status,
                    "attendance_credit": float(r.attendance_credit),
                    "checkpoints_verified": r.checkpoints_verified,
                    "start_credited": r.start_credited,
                    "middle_credited": r.middle_credited,
                    "end_credited": r.end_credited,
                    "is_manual": r.is_manual,
                    "finalized_at_utc": r.finalized_at_utc,
                }
            )
        return results

    @staticmethod
    async def get_attendance_audit_log(
        db: AsyncSession,
        session_id: uuid.UUID | None = None,
        record_id: uuid.UUID | None = None,
    ) -> list[AttendanceRevision]:
        """Query immutable revision ledger."""
        stmt = select(AttendanceRevision)
        if session_id:
            stmt = stmt.where(AttendanceRevision.attendance_session_id == session_id)
        if record_id:
            stmt = stmt.where(AttendanceRevision.attendance_record_id == record_id)
        stmt = stmt.order_by(AttendanceRevision.occurred_at_utc.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())
