"""Attendance Operations Service implementing corrections, excuses, and immutable revisions.

Enforces:
- INV-01: Client cannot mark itself present; only authorized workflows update attendance.
- INV-02: Server UTC clock is the sole authority for correction windows.
- INV-06: Corrections cannot erase history; append-only revision ledger.
- INV-08: Manual adjustments and overrides require recorded justification and actor ID.
"""

import datetime
import uuid

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from backend.app.attendance.operations_schemas import (
    AdminOverrideRequest,
    BulkItemResult,
    BulkReviewRequest,
    BulkReviewResponse,
    CorrectionRequestCreate,
    CorrectionRequestReview,
    ExcuseRequestCreate,
    ExcuseRequestReview,
    LeaveRequestCreate,
    LeaveRequestReview,
    ManualReviewConfirmRequest,
    ManualReviewItemResponse,
    OperationsCountsResponse,
    RecordEligibilityResponse,
    RecordTimelineResponse,
    RevisionItemResponse,
    RevisionReversalRequest,
)
from backend.app.common.types import utc_now
from backend.app.core.constants import (
    AttendanceAuditEventType,
    AttendanceStatus,
    CorrectionRequestStatus,
    ExcuseRequestStatus,
    LeaveRequestStatus,
    SystemRole,
)
from backend.app.core.exceptions import (
    ConflictException,
    DomainException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from backend.app.models.attendance_correction import (
    AttendanceCorrectionRequest,
    AttendanceExcuseRequest,
    AttendanceLeaveRequest,
)
from backend.app.models.attendance_policy import DEFAULT_STATUS_CREDIT
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.attendance_revision import AttendanceRevision
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.class_occurrence import ClassOccurrence
from backend.app.models.course_offering import CourseOffering
from backend.app.models.lecturer import Lecturer
from backend.app.models.lecturer_assignment import LecturerAssignment
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.rbac.service import RbacService


class AttendanceOperationsService:
    """Core domain operations service for attendance adjustments, reviews, and revisions."""

    # =========================================================================
    # 1. Helper / Scope Resolution Methods
    # =========================================================================

    @staticmethod
    async def get_student_for_user(db: AsyncSession, user_id: uuid.UUID) -> Student:
        """Resolve student profile bound to the authenticated user."""
        stmt = select(Student).where(Student.user_id == user_id)
        res = await db.execute(stmt)
        student = res.scalar_one_or_none()
        if not student:
            raise ForbiddenException("User does not have an associated student profile.")
        return student

    @staticmethod
    def check_correction_window(
        session: AttendanceSession,
        occurrence: ClassOccurrence | None = None,
    ) -> tuple[bool, datetime.datetime]:
        """Verify whether current server UTC time is within the session's correction window."""
        now = utc_now()
        policy_snapshot = session.policy_snapshot or {}
        window_hours = int(policy_snapshot.get("lecturer_correction_window_hours", 24))

        # Reference point: session closed_at_utc preferred; fallback to occurrence end
        start_ref = session.closed_at_utc

        if not start_ref and occurrence:
            start_ref = occurrence.scheduled_end_utc
        if not start_ref:
            start_ref = session.created_at

        deadline = start_ref + datetime.timedelta(hours=window_hours)
        return (now <= deadline, deadline)

    @staticmethod
    async def verify_reviewer_scope(
        db: AsyncSession,
        user: User,
        session: AttendanceSession,
    ) -> None:
        """Verify reviewer has academic or administrative authority over the session."""
        if session.university_id != user.university_id:
            raise ForbiddenException("Reviewer does not belong to the same institution.")

        user_roles = set(await RbacService.get_user_roles(db, user.id))
        admin_roles = {
            SystemRole.SUPER_ADMIN.value,
            SystemRole.UNIVERSITY_ADMIN.value,
            SystemRole.ATTENDANCE_OFFICER.value,
            SystemRole.FACULTY_ADMIN.value,
            SystemRole.DEPARTMENT_ADMIN.value,
        }
        if user_roles & admin_roles:
            return

        stmt = select(ClassOccurrence).where(ClassOccurrence.id == session.class_occurrence_id)
        res = await db.execute(stmt)
        occurrence = res.scalar_one_or_none()
        if not occurrence:
            raise NotFoundException("ClassOccurrence", session.class_occurrence_id)

        lec_stmt = select(Lecturer).where(Lecturer.user_id == user.id)
        lec_res = await db.execute(lec_stmt)
        lecturer = lec_res.scalar_one_or_none()
        if lecturer:
            if (
                occurrence.lecturer_id == lecturer.id
                or occurrence.substitute_lecturer_id == lecturer.id
            ):
                return
            if occurrence.course_offering_id:
                assign_stmt = select(LecturerAssignment).where(
                    LecturerAssignment.course_offering_id == occurrence.course_offering_id,
                    LecturerAssignment.lecturer_id == lecturer.id,
                )
                assign_res = await db.execute(assign_stmt)
                if assign_res.scalar_one_or_none():
                    return

        raise ForbiddenException(
            "You do not have authorization to review attendance requests for this class."
        )

    # =========================================================================
    # 2. Student Correction Request Workflow
    # =========================================================================

    @staticmethod
    async def submit_correction_request(
        db: AsyncSession,
        user: User,
        dto: CorrectionRequestCreate,
    ) -> AttendanceCorrectionRequest:
        """Student submits a correction request for their record in allowed window."""
        student = await AttendanceOperationsService.get_student_for_user(db, user.id)

        # Fetch attendance record and verify ownership
        stmt = (
            select(AttendanceRecord)
            .options(
                selectinload(AttendanceRecord.session).selectinload(
                    AttendanceSession.class_occurrence
                )
            )
            .where(AttendanceRecord.id == dto.attendance_record_id)
        )
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            raise NotFoundException("AttendanceRecord", dto.attendance_record_id)

        if record.student_id != student.id:
            raise ForbiddenException(
                "Students may only request corrections for their own attendance records."
            )

        session = record.session
        occurrence = session.class_occurrence if session else None

        # Verify correction window (INV-02: Server UTC authority)
        is_within_window, deadline = AttendanceOperationsService.check_correction_window(
            session, occurrence
        )
        if not is_within_window:
            raise DomainException(
                code="CORRECTION_WINDOW_EXPIRED",
                message=(
                    f"The correction window for this session expired at {deadline.isoformat()} UTC."
                ),
                status_code=400,
                details={"window_deadline": deadline.isoformat()},
            )

        # Check one open request rule per attendance record
        check_stmt = select(AttendanceCorrectionRequest).where(
            AttendanceCorrectionRequest.attendance_record_id == record.id,
            AttendanceCorrectionRequest.status.in_(
                [
                    CorrectionRequestStatus.PENDING.value,
                    CorrectionRequestStatus.UNDER_REVIEW.value,
                ]
            ),
        )
        existing = (await db.execute(check_stmt)).scalar_one_or_none()
        if existing:
            raise ConflictException(
                "An open correction request already exists for this attendance record.",
                code="DUPLICATE_OPEN_REQUEST",
            )

        # Create request
        correction_req = AttendanceCorrectionRequest(
            university_id=session.university_id,
            attendance_record_id=record.id,
            attendance_session_id=session.id,
            student_id=student.id,
            request_type=dto.request_type.value,
            requested_status=dto.requested_status.value,
            reason=dto.reason.strip(),
            supporting_note=dto.supporting_note.strip() if dto.supporting_note else None,
            status=CorrectionRequestStatus.PENDING.value,
        )
        db.add(correction_req)

        # Append audit revision event for request submission (INV-06)
        audit_event = AttendanceRevision(
            attendance_session_id=session.id,
            attendance_record_id=record.id,
            actor_user_id=user.id,
            event_type=AttendanceAuditEventType.CORRECTION_REQUESTED.value,
            previous_status=record.status,
            new_status=record.status,
            previous_credit=float(record.attendance_credit),
            new_credit=float(record.attendance_credit),
            reason=f"Correction requested ({dto.request_type.value}): {dto.reason.strip()}",
            metadata_json={"requested_status": dto.requested_status.value},
            occurred_at_utc=utc_now(),
        )
        db.add(audit_event)

        await db.commit()
        await db.refresh(correction_req)
        return correction_req

    @staticmethod
    async def cancel_correction_request(
        db: AsyncSession,
        user: User,
        request_id: uuid.UUID,
    ) -> AttendanceCorrectionRequest:
        """Student cancels their own pending correction request before review begins."""
        student = await AttendanceOperationsService.get_student_for_user(db, user.id)

        stmt = select(AttendanceCorrectionRequest).where(
            AttendanceCorrectionRequest.id == request_id
        )
        res = await db.execute(stmt)
        req = res.scalar_one_or_none()
        if not req:
            raise NotFoundException("AttendanceCorrectionRequest", request_id)

        if req.student_id != student.id:
            raise ForbiddenException("Students may only cancel their own correction requests.")

        if req.status != CorrectionRequestStatus.PENDING.value:
            raise DomainException(
                code="INVALID_REQUEST_STATE",
                message=f"Only PENDING requests can be cancelled. Current status is {req.status}.",
                status_code=400,
            )

        req.status = CorrectionRequestStatus.CANCELLED.value
        now = utc_now()

        audit_event = AttendanceRevision(
            attendance_session_id=req.attendance_session_id,
            attendance_record_id=req.attendance_record_id,
            actor_user_id=user.id,
            event_type=AttendanceAuditEventType.CORRECTION_CANCELLED.value,
            reason="Correction request cancelled by student.",
            metadata_json={"request_id": str(req.id)},
            occurred_at_utc=now,
        )
        db.add(audit_event)

        await db.commit()
        await db.refresh(req)
        return req

    # =========================================================================
    # 3. Reviewer Action: Approval & Rejection (INV-06, INV-08)
    # =========================================================================

    @staticmethod
    async def review_correction_request(
        db: AsyncSession,
        user: User,
        request_id: uuid.UUID,
        dto: CorrectionRequestReview,
        auto_commit: bool = True,
    ) -> AttendanceCorrectionRequest:
        """Review, approve, or reject an attendance correction request with row-level locking."""
        if dto.status not in (CorrectionRequestStatus.APPROVED, CorrectionRequestStatus.REJECTED):
            raise ValidationException("Review status must be either APPROVED or REJECTED.")

        # Row-lock request
        stmt = (
            select(AttendanceCorrectionRequest)
            .where(AttendanceCorrectionRequest.id == request_id)
            .with_for_update()
        )
        res = await db.execute(stmt)
        req = res.scalar_one_or_none()
        if not req:
            raise NotFoundException("AttendanceCorrectionRequest", request_id)

        if req.status not in (
            CorrectionRequestStatus.PENDING.value,
            CorrectionRequestStatus.UNDER_REVIEW.value,
        ):
            raise DomainException(
                code="REQUEST_ALREADY_RESOLVED",
                message=f"Correction request is already {req.status}.",
                status_code=400,
            )

        # Row-lock attendance record
        rec_stmt = (
            select(AttendanceRecord)
            .where(AttendanceRecord.id == req.attendance_record_id)
            .with_for_update()
        )
        rec_res = await db.execute(rec_stmt)
        record = rec_res.scalar_one_or_none()
        if not record:
            raise NotFoundException("AttendanceRecord", req.attendance_record_id)

        # Fetch session for policy and scope verification
        session = await db.get(AttendanceSession, req.attendance_session_id)
        if not session:
            raise NotFoundException("AttendanceSession", req.attendance_session_id)

        await AttendanceOperationsService.verify_reviewer_scope(db, user, session)

        now = utc_now()
        req.reviewed_by_user_id = user.id
        req.reviewed_at_utc = now
        req.review_note = dto.review_note.strip()

        if dto.status == CorrectionRequestStatus.APPROVED:
            target_status = dto.approved_status or AttendanceStatus(req.requested_status)
            prev_status = record.status
            prev_credit = float(record.attendance_credit)

            # Calculate new credit according to policy snapshot
            policy_snapshot = session.policy_snapshot or {}
            status_credit_map = policy_snapshot.get("status_credit", DEFAULT_STATUS_CREDIT)

            if target_status.value in status_credit_map:
                calculated_credit = float(status_credit_map[target_status.value])
            elif target_status == AttendanceStatus.PRESENT:
                calculated_credit = 1.0
            elif target_status == AttendanceStatus.LATE:
                calculated_credit = 0.5
            elif target_status == AttendanceStatus.EXCUSED:
                calculated_credit = float(policy_snapshot.get("excused_credit", 0.0))
            elif target_status == AttendanceStatus.LEAVE:
                calculated_credit = 0.0  # LEAVE does not grant attendance credit
            else:
                calculated_credit = 0.0

            # Update record
            record.status = target_status.value
            record.attendance_credit = calculated_credit
            record.is_manual = True
            record.manual_reason = f"Correction approved: {dto.review_note.strip()}"
            record.version_no += 1
            record.finalized_at_utc = now

            req.status = CorrectionRequestStatus.APPROVED.value

            # Append immutable revision (INV-06, INV-08)
            revision = AttendanceRevision(
                attendance_session_id=session.id,
                attendance_record_id=record.id,
                actor_user_id=user.id,
                event_type=AttendanceAuditEventType.CORRECTION_APPROVED.value,
                previous_status=prev_status,
                new_status=target_status.value,
                previous_credit=prev_credit,
                new_credit=calculated_credit,
                reason=f"Correction approved: {dto.review_note.strip()}",
                metadata_json={
                    "request_id": str(req.id),
                    "request_type": req.request_type,
                    "student_reason": req.reason,
                    "reviewer_note": dto.review_note.strip(),
                },
                occurred_at_utc=now,
            )
            db.add(revision)

        else:
            # Rejection preserves historical record
            req.status = CorrectionRequestStatus.REJECTED.value

            revision = AttendanceRevision(
                attendance_session_id=session.id,
                attendance_record_id=record.id,
                actor_user_id=user.id,
                event_type=AttendanceAuditEventType.CORRECTION_REJECTED.value,
                previous_status=record.status,
                new_status=record.status,
                previous_credit=float(record.attendance_credit),
                new_credit=float(record.attendance_credit),
                reason=f"Correction rejected: {dto.review_note.strip()}",
                metadata_json={
                    "request_id": str(req.id),
                    "request_type": req.request_type,
                    "student_reason": req.reason,
                    "reviewer_note": dto.review_note.strip(),
                },
                occurred_at_utc=now,
            )
            db.add(revision)

        if auto_commit:
            await db.commit()
            await db.refresh(req)
        else:
            await db.flush()
        return req

    # =========================================================================
    # 4. Privileged Admin Override & Reversals (INV-06, INV-08)
    # =========================================================================

    @staticmethod
    async def admin_override(
        db: AsyncSession,
        user: User,
        dto: AdminOverrideRequest,
    ) -> AttendanceRecord:
        """Privileged administrative status override outside or independent of student requests."""
        rec_stmt = (
            select(AttendanceRecord)
            .where(AttendanceRecord.id == dto.attendance_record_id)
            .with_for_update()
        )
        rec_res = await db.execute(rec_stmt)
        record = rec_res.scalar_one_or_none()
        if not record:
            raise NotFoundException("AttendanceRecord", dto.attendance_record_id)

        session = await db.get(AttendanceSession, record.attendance_session_id)
        if not session:
            raise NotFoundException("AttendanceSession", record.attendance_session_id)

        if session.university_id != user.university_id:
            raise ForbiddenException("Administrator does not belong to the session university.")

        now = utc_now()
        prev_status = record.status
        prev_credit = float(record.attendance_credit)

        # Determine credit
        policy_snapshot = session.policy_snapshot or {}
        status_credit_map = policy_snapshot.get("status_credit", DEFAULT_STATUS_CREDIT)

        if dto.target_credit is not None:
            calculated_credit = dto.target_credit
        elif dto.target_status.value in status_credit_map:
            calculated_credit = float(status_credit_map[dto.target_status.value])
        elif dto.target_status == AttendanceStatus.PRESENT:
            calculated_credit = 1.0
        elif dto.target_status == AttendanceStatus.LATE:
            calculated_credit = 0.5
        elif dto.target_status == AttendanceStatus.EXCUSED:
            calculated_credit = float(policy_snapshot.get("excused_credit", 0.0))
        elif dto.target_status == AttendanceStatus.LEAVE:
            calculated_credit = 0.0
        else:
            calculated_credit = 0.0

        record.status = dto.target_status.value
        record.attendance_credit = calculated_credit
        record.is_manual = True
        record.manual_reason = f"Admin override: {dto.reason.strip()}"
        record.version_no += 1
        record.finalized_at_utc = now

        revision = AttendanceRevision(
            attendance_session_id=session.id,
            attendance_record_id=record.id,
            actor_user_id=user.id,
            event_type=AttendanceAuditEventType.ADMIN_OVERRIDE.value,
            previous_status=prev_status,
            new_status=dto.target_status.value,
            previous_credit=prev_credit,
            new_credit=calculated_credit,
            reason=f"Admin override: {dto.reason.strip()}",
            metadata_json={"is_admin_override": True},
            occurred_at_utc=now,
        )
        db.add(revision)

        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def reverse_revision(
        db: AsyncSession,
        user: User,
        dto: RevisionReversalRequest,
    ) -> AttendanceRecord:
        """Reverse prior revision by creating a compensating revision without modifying history."""
        rev_stmt = select(AttendanceRevision).where(AttendanceRevision.id == dto.revision_id)
        rev_res = await db.execute(rev_stmt)
        prior_revision = rev_res.scalar_one_or_none()
        if not prior_revision:
            raise NotFoundException("AttendanceRevision", dto.revision_id)

        if not prior_revision.attendance_record_id:
            raise DomainException(
                code="RECORD_REVISION_REQUIRED",
                message="Cannot reverse a revision not bound to an individual attendance record.",
                status_code=400,
            )

        rec_stmt = (
            select(AttendanceRecord)
            .where(AttendanceRecord.id == prior_revision.attendance_record_id)
            .with_for_update()
        )
        rec_res = await db.execute(rec_stmt)
        record = rec_res.scalar_one_or_none()
        if not record:
            raise NotFoundException("AttendanceRecord", prior_revision.attendance_record_id)

        session = await db.get(AttendanceSession, record.attendance_session_id)
        if not session:
            raise NotFoundException("AttendanceSession", record.attendance_session_id)

        await AttendanceOperationsService.verify_reviewer_scope(db, user, session)

        now = utc_now()
        prev_status = record.status
        prev_credit = float(record.attendance_credit)

        # Revert to the prior revision's previous_status (or ABSENT if None)
        reverted_status = prior_revision.previous_status or AttendanceStatus.ABSENT.value
        reverted_credit = (
            prior_revision.previous_credit if prior_revision.previous_credit is not None else 0.0
        )

        record.status = reverted_status
        record.attendance_credit = float(reverted_credit)
        record.is_manual = True
        record.manual_reason = f"Reversal of revision {prior_revision.id}: {dto.reason.strip()}"
        record.version_no += 1
        record.finalized_at_utc = now

        # Create NEW revision documenting the reversal (INV-06)
        comp_revision = AttendanceRevision(
            attendance_session_id=session.id,
            attendance_record_id=record.id,
            actor_user_id=user.id,
            event_type=AttendanceAuditEventType.REVERSAL.value,
            previous_status=prev_status,
            new_status=reverted_status,
            previous_credit=prev_credit,
            new_credit=float(reverted_credit),
            reason=f"Reversal of revision {prior_revision.id}: {dto.reason.strip()}",
            metadata_json={
                "reversed_revision_id": str(prior_revision.id),
                "original_event_type": prior_revision.event_type,
            },
            occurred_at_utc=now,
        )
        db.add(comp_revision)

        await db.commit()
        await db.refresh(record)
        return record

    # =========================================================================
    # 5. Absence Excuse Workflow
    # =========================================================================

    @staticmethod
    async def submit_excuse_request(
        db: AsyncSession,
        user: User,
        dto: ExcuseRequestCreate,
    ) -> AttendanceExcuseRequest:
        """Student submits an absence excuse request for a session or occurrence."""
        student = await AttendanceOperationsService.get_student_for_user(db, user.id)

        session_id = dto.attendance_session_id
        occurrence_id = dto.class_occurrence_id

        if not session_id and not occurrence_id:
            raise ValidationException(
                "Either attendance_session_id or class_occurrence_id must be provided."
            )

        university_id = user.university_id

        # Enforce one open request rule per session/occurrence
        conds = []
        if session_id:
            conds.append(AttendanceExcuseRequest.attendance_session_id == session_id)
        if occurrence_id:
            conds.append(AttendanceExcuseRequest.class_occurrence_id == occurrence_id)

        dup_stmt = select(AttendanceExcuseRequest).where(
            AttendanceExcuseRequest.student_id == student.id,
            or_(*conds),
            AttendanceExcuseRequest.status.in_(
                [
                    ExcuseRequestStatus.PENDING.value,
                    ExcuseRequestStatus.UNDER_REVIEW.value,
                ]
            ),
        )
        existing = (await db.execute(dup_stmt)).scalar_one_or_none()
        if existing:
            raise ConflictException(
                "An open excuse request already exists for this session or occurrence.",
                code="DUPLICATE_OPEN_EXCUSE",
            )

        excuse_req = AttendanceExcuseRequest(
            university_id=university_id,
            student_id=student.id,
            attendance_record_id=dto.attendance_record_id,
            attendance_session_id=session_id,
            class_occurrence_id=occurrence_id,
            category=dto.category.value,
            description=dto.description.strip(),
            document_reference=dto.document_reference.strip() if dto.document_reference else None,
            status=ExcuseRequestStatus.PENDING.value,
        )
        db.add(excuse_req)
        await db.commit()
        await db.refresh(excuse_req)
        return excuse_req

    @staticmethod
    async def review_excuse_request(
        db: AsyncSession,
        user: User,
        request_id: uuid.UUID,
        dto: ExcuseRequestReview,
        auto_commit: bool = True,
    ) -> AttendanceExcuseRequest:
        """Review, approve, or reject an absence excuse request."""
        stmt = (
            select(AttendanceExcuseRequest)
            .where(AttendanceExcuseRequest.id == request_id)
            .with_for_update()
        )
        res = await db.execute(stmt)
        req = res.scalar_one_or_none()
        if not req:
            raise NotFoundException("AttendanceExcuseRequest", request_id)

        if req.status not in (
            ExcuseRequestStatus.PENDING.value,
            ExcuseRequestStatus.UNDER_REVIEW.value,
        ):
            raise DomainException(
                code="REQUEST_ALREADY_RESOLVED",
                message=f"Excuse request is already {req.status}.",
                status_code=400,
            )

        now = utc_now()
        req.reviewed_by_user_id = user.id
        req.reviewed_at_utc = now
        req.review_note = dto.review_note.strip()

        if dto.status == ExcuseRequestStatus.APPROVED:
            req.status = ExcuseRequestStatus.APPROVED.value

            # If an attendance record is linked or exists for this session, update it
            if req.attendance_session_id:
                rec_stmt = (
                    select(AttendanceRecord)
                    .where(
                        AttendanceRecord.attendance_session_id == req.attendance_session_id,
                        AttendanceRecord.student_id == req.student_id,
                    )
                    .with_for_update()
                )
                rec = (await db.execute(rec_stmt)).scalar_one_or_none()
                if rec:
                    session = await db.get(AttendanceSession, req.attendance_session_id)
                    policy_snapshot = session.policy_snapshot if session else {}
                    excused_credit = float(policy_snapshot.get("excused_credit", 0.0))

                    prev_status = rec.status
                    prev_credit = float(rec.attendance_credit)

                    rec.status = AttendanceStatus.EXCUSED.value
                    rec.attendance_credit = excused_credit
                    rec.is_manual = True
                    rec.manual_reason = (
                        f"Excuse approved ({req.category}): {dto.review_note.strip()}"
                    )
                    rec.version_no += 1
                    rec.finalized_at_utc = now

                    revision = AttendanceRevision(
                        attendance_session_id=req.attendance_session_id,
                        attendance_record_id=rec.id,
                        actor_user_id=user.id,
                        event_type=AttendanceAuditEventType.EXCUSE_APPROVED.value,
                        previous_status=prev_status,
                        new_status=AttendanceStatus.EXCUSED.value,
                        previous_credit=prev_credit,
                        new_credit=excused_credit,
                        reason=f"Excuse approved ({req.category}): {dto.review_note.strip()}",
                        metadata_json={
                            "excuse_request_id": str(req.id),
                            "category": req.category,
                        },
                        occurred_at_utc=now,
                    )
                    db.add(revision)
        else:
            req.status = ExcuseRequestStatus.REJECTED.value

        if auto_commit:
            await db.commit()
            await db.refresh(req)
        else:
            await db.flush()
        return req

    # =========================================================================
    # 6. Pre-Class Leave Workflow (Section 35-38)
    # =========================================================================

    @staticmethod
    async def submit_leave_request(
        db: AsyncSession,
        user: User,
        dto: LeaveRequestCreate,
    ) -> AttendanceLeaveRequest:
        """Student submits a pre-class leave request for a class occurrence."""
        student = await AttendanceOperationsService.get_student_for_user(db, user.id)

        occurrence = await db.get(ClassOccurrence, dto.class_occurrence_id)
        if not occurrence:
            raise NotFoundException("ClassOccurrence", dto.class_occurrence_id)

        # Enforce one open leave request rule per occurrence
        check_stmt = select(AttendanceLeaveRequest).where(
            AttendanceLeaveRequest.student_id == student.id,
            AttendanceLeaveRequest.class_occurrence_id == dto.class_occurrence_id,
            AttendanceLeaveRequest.status.in_(
                [
                    LeaveRequestStatus.PENDING.value,
                    LeaveRequestStatus.UNDER_REVIEW.value,
                ]
            ),
        )
        existing = (await db.execute(check_stmt)).scalar_one_or_none()
        if existing:
            raise ConflictException(
                "An open leave request already exists for this class occurrence.",
                code="DUPLICATE_OPEN_LEAVE",
            )

        leave_req = AttendanceLeaveRequest(
            university_id=user.university_id,
            student_id=student.id,
            class_occurrence_id=dto.class_occurrence_id,
            reason=dto.reason.strip(),
            status=LeaveRequestStatus.PENDING.value,
        )
        db.add(leave_req)
        await db.commit()
        await db.refresh(leave_req)
        return leave_req

    @staticmethod
    async def review_leave_request(
        db: AsyncSession,
        user: User,
        request_id: uuid.UUID,
        dto: LeaveRequestReview,
        auto_commit: bool = True,
    ) -> AttendanceLeaveRequest:
        """Review, approve, or reject pre-class leave request (LEAVE grants 0 credit)."""
        stmt = (
            select(AttendanceLeaveRequest)
            .where(AttendanceLeaveRequest.id == request_id)
            .with_for_update()
        )
        res = await db.execute(stmt)
        req = res.scalar_one_or_none()
        if not req:
            raise NotFoundException("AttendanceLeaveRequest", request_id)

        if req.status not in (
            LeaveRequestStatus.PENDING.value,
            LeaveRequestStatus.UNDER_REVIEW.value,
        ):
            raise DomainException(
                code="REQUEST_ALREADY_RESOLVED",
                message=f"Leave request is already {req.status}.",
                status_code=400,
            )

        now = utc_now()
        req.reviewed_by_user_id = user.id
        req.reviewed_at_utc = now
        req.review_note = dto.review_note.strip()

        if dto.status == LeaveRequestStatus.APPROVED:
            req.status = LeaveRequestStatus.APPROVED.value

            # If attendance session and record already exist for this occurrence, apply LEAVE status
            sess_stmt = select(AttendanceSession).where(
                AttendanceSession.class_occurrence_id == req.class_occurrence_id
            )
            session = (await db.execute(sess_stmt)).scalar_one_or_none()
            if session:
                rec_stmt = (
                    select(AttendanceRecord)
                    .where(
                        AttendanceRecord.attendance_session_id == session.id,
                        AttendanceRecord.student_id == req.student_id,
                    )
                    .with_for_update()
                )
                rec = (await db.execute(rec_stmt)).scalar_one_or_none()
                if rec:
                    prev_status = rec.status
                    prev_credit = float(rec.attendance_credit)

                    # LEAVE status with 0.0 credit (Section 38: do not count as checkpoint credit)
                    rec.status = AttendanceStatus.LEAVE.value
                    rec.attendance_credit = 0.0
                    rec.is_manual = True
                    rec.manual_reason = f"Approved leave: {dto.review_note.strip()}"
                    rec.version_no += 1
                    rec.finalized_at_utc = now

                    revision = AttendanceRevision(
                        attendance_session_id=session.id,
                        attendance_record_id=rec.id,
                        actor_user_id=user.id,
                        event_type=AttendanceAuditEventType.LEAVE_APPROVED.value,
                        previous_status=prev_status,
                        new_status=AttendanceStatus.LEAVE.value,
                        previous_credit=prev_credit,
                        new_credit=0.0,
                        reason=f"Approved leave: {dto.review_note.strip()}",
                        metadata_json={"leave_request_id": str(req.id)},
                        occurred_at_utc=now,
                    )
                    db.add(revision)
        else:
            req.status = LeaveRequestStatus.REJECTED.value

        if auto_commit:
            await db.commit()
            await db.refresh(req)
        else:
            await db.flush()
        return req

    # =========================================================================
    # 7. Queries & Audit Timeline (INV-06)
    # =========================================================================

    @staticmethod
    async def get_record_timeline(
        db: AsyncSession,
        record_id: uuid.UUID,
    ) -> RecordTimelineResponse:
        """Fetch comprehensive timeline of an attendance record and its revisions."""
        rec_stmt = (
            select(AttendanceRecord)
            .options(selectinload(AttendanceRecord.revisions))
            .where(AttendanceRecord.id == record_id)
        )
        res = await db.execute(rec_stmt)
        record = res.scalar_one_or_none()
        if not record:
            raise NotFoundException("AttendanceRecord", record_id)

        sorted_revisions = sorted(record.revisions, key=lambda r: r.occurred_at_utc)

        return RecordTimelineResponse(
            record_id=record.id,
            session_id=record.attendance_session_id,
            student_id=record.student_id,
            current_status=record.status,
            current_credit=float(record.attendance_credit),
            version_no=record.version_no,
            is_manual=record.is_manual,
            manual_reason=record.manual_reason,
            revisions=[RevisionItemResponse.model_validate(r) for r in sorted_revisions],
        )

    @staticmethod
    async def get_student_correction_requests(
        db: AsyncSession,
        user: User,
    ) -> list[AttendanceCorrectionRequest]:
        """Fetch all correction requests submitted by the student."""
        student = await AttendanceOperationsService.get_student_for_user(db, user.id)
        stmt = (
            select(AttendanceCorrectionRequest)
            .where(AttendanceCorrectionRequest.student_id == student.id)
            .order_by(desc(AttendanceCorrectionRequest.created_at))
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_reviewer_queue(
        db: AsyncSession,
        user: User,
        status_filter: CorrectionRequestStatus | None = None,
    ) -> list[AttendanceCorrectionRequest]:
        """Fetch queue of correction requests reviewable by the user."""
        stmt = select(AttendanceCorrectionRequest).where(
            AttendanceCorrectionRequest.university_id == user.university_id
        )
        if status_filter:
            stmt = stmt.where(AttendanceCorrectionRequest.status == status_filter.value)
        stmt = stmt.order_by(desc(AttendanceCorrectionRequest.created_at))
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_excuse_queue(
        db: AsyncSession,
        user: User,
        status_filter: ExcuseRequestStatus | None = None,
    ) -> list[AttendanceExcuseRequest]:
        """Fetch queue of excuse requests reviewable by the user."""
        stmt = select(AttendanceExcuseRequest).where(
            AttendanceExcuseRequest.university_id == user.university_id
        )
        if status_filter:
            stmt = stmt.where(AttendanceExcuseRequest.status == status_filter.value)
        stmt = stmt.order_by(desc(AttendanceExcuseRequest.created_at))
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_student_excuses(
        db: AsyncSession,
        user: User,
    ) -> list[AttendanceExcuseRequest]:
        """Fetch all excuse requests submitted by the student."""
        student = await AttendanceOperationsService.get_student_for_user(db, user.id)
        stmt = (
            select(AttendanceExcuseRequest)
            .where(AttendanceExcuseRequest.student_id == student.id)
            .order_by(desc(AttendanceExcuseRequest.created_at))
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_leave_queue(
        db: AsyncSession,
        user: User,
        status_filter: LeaveRequestStatus | None = None,
    ) -> list[AttendanceLeaveRequest]:
        """Fetch queue of leave requests reviewable by the user."""
        stmt = select(AttendanceLeaveRequest).where(
            AttendanceLeaveRequest.university_id == user.university_id
        )
        if status_filter:
            stmt = stmt.where(AttendanceLeaveRequest.status == status_filter.value)
        stmt = stmt.order_by(desc(AttendanceLeaveRequest.created_at))
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_student_leaves(
        db: AsyncSession,
        user: User,
    ) -> list[AttendanceLeaveRequest]:
        """Fetch all pre-class leave requests submitted by the student."""
        student = await AttendanceOperationsService.get_student_for_user(db, user.id)
        stmt = (
            select(AttendanceLeaveRequest)
            .where(AttendanceLeaveRequest.student_id == student.id)
            .order_by(desc(AttendanceLeaveRequest.created_at))
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def bulk_review(
        db: AsyncSession,
        user: User,
        dto: BulkReviewRequest,
    ) -> BulkReviewResponse:
        """Safely process a batch of review decisions with itemized isolation."""
        succeeded = 0
        failed = 0
        results: list[BulkItemResult] = []

        for item_id in dto.request_ids:
            try:
                async with db.begin_nested():
                    if dto.request_type == "correction":
                        await AttendanceOperationsService.review_correction_request(
                            db,
                            user,
                            item_id,
                            CorrectionRequestReview(
                                status=CorrectionRequestStatus(dto.status),
                                approved_status=dto.approved_status,
                                review_note=dto.review_note,
                            ),
                            auto_commit=False,
                        )
                    elif dto.request_type == "excuse":
                        await AttendanceOperationsService.review_excuse_request(
                            db,
                            user,
                            item_id,
                            ExcuseRequestReview(
                                status=ExcuseRequestStatus(dto.status),
                                review_note=dto.review_note,
                            ),
                            auto_commit=False,
                        )
                    elif dto.request_type == "leave":
                        await AttendanceOperationsService.review_leave_request(
                            db,
                            user,
                            item_id,
                            LeaveRequestReview(
                                status=LeaveRequestStatus(dto.status),
                                review_note=dto.review_note,
                            ),
                            auto_commit=False,
                        )
                    else:
                        raise ValidationException(f"Unsupported request type: {dto.request_type}")
                succeeded += 1
                results.append(BulkItemResult(id=item_id, success=True, status=dto.status))
            except Exception as e:
                failed += 1
                results.append(BulkItemResult(id=item_id, success=False, error=str(e)))

        await db.commit()
        return BulkReviewResponse(
            total=len(dto.request_ids),
            succeeded=succeeded,
            failed=failed,
            results=results,
        )

    @staticmethod
    async def get_operations_counts(
        db: AsyncSession,
        user: User,
    ) -> OperationsCountsResponse:
        """Pending counts for attendance operations dashboard tabs."""
        corr_stmt = select(func.count(AttendanceCorrectionRequest.id)).where(
            AttendanceCorrectionRequest.university_id == user.university_id,
            AttendanceCorrectionRequest.status == CorrectionRequestStatus.PENDING.value,
        )
        pending_corrections = (await db.execute(corr_stmt)).scalar() or 0

        exc_stmt = select(func.count(AttendanceExcuseRequest.id)).where(
            AttendanceExcuseRequest.university_id == user.university_id,
            AttendanceExcuseRequest.status == ExcuseRequestStatus.PENDING.value,
        )
        pending_excuses = (await db.execute(exc_stmt)).scalar() or 0

        leave_stmt = select(func.count(AttendanceLeaveRequest.id)).where(
            AttendanceLeaveRequest.university_id == user.university_id,
            AttendanceLeaveRequest.status == LeaveRequestStatus.PENDING.value,
        )
        pending_leaves = (await db.execute(leave_stmt)).scalar() or 0

        man_stmt = (
            select(func.count(AttendanceRecord.id))
            .join(AttendanceSession, AttendanceRecord.attendance_session_id == AttendanceSession.id)
            .where(
                AttendanceSession.university_id == user.university_id,
                AttendanceRecord.is_manual == True,  # noqa: E712
            )
        )
        manual_reviews = (await db.execute(man_stmt)).scalar() or 0

        return OperationsCountsResponse(
            pending_corrections=pending_corrections,
            pending_excuses=pending_excuses,
            pending_leaves=pending_leaves,
            manual_reviews=manual_reviews,
        )

    @staticmethod
    async def check_record_eligibility(
        db: AsyncSession,
        user: User,
        record_id: uuid.UUID,
    ) -> RecordEligibilityResponse:
        """Verify if a student/record is eligible to request an attendance correction."""
        stmt = (
            select(AttendanceRecord)
            .options(
                selectinload(AttendanceRecord.session).selectinload(
                    AttendanceSession.class_occurrence
                )
            )
            .where(AttendanceRecord.id == record_id)
        )
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            raise NotFoundException("AttendanceRecord", record_id)

        session = record.session
        occurrence = session.class_occurrence if session else None

        is_within_window, deadline = AttendanceOperationsService.check_correction_window(
            session, occurrence
        )

        corr_stmt = select(AttendanceCorrectionRequest).where(
            AttendanceCorrectionRequest.attendance_record_id == record.id,
            AttendanceCorrectionRequest.status.in_(
                [
                    CorrectionRequestStatus.PENDING.value,
                    CorrectionRequestStatus.UNDER_REVIEW.value,
                ]
            ),
        )
        has_open_correction = (await db.execute(corr_stmt)).scalar_one_or_none() is not None

        exc_stmt = select(AttendanceExcuseRequest).where(
            AttendanceExcuseRequest.attendance_record_id == record.id,
            AttendanceExcuseRequest.status.in_(
                [
                    ExcuseRequestStatus.PENDING.value,
                    ExcuseRequestStatus.UNDER_REVIEW.value,
                ]
            ),
        )
        has_open_excuse = (await db.execute(exc_stmt)).scalar_one_or_none() is not None

        eligible = is_within_window and not has_open_correction
        reason = None
        if not is_within_window:
            reason = f"Correction window expired at {deadline.isoformat()} UTC."
        elif has_open_correction:
            reason = "An open correction request is already pending for this record."

        return RecordEligibilityResponse(
            record_id=record.id,
            eligible_for_correction=eligible,
            correction_ineligibility_reason=reason,
            correction_window_deadline_utc=deadline,
            has_open_correction=has_open_correction,
            has_open_excuse=has_open_excuse,
            current_status=record.status,
            current_credit=float(record.attendance_credit),
        )

    @staticmethod
    async def get_manual_reviews_queue(
        db: AsyncSession,
        user: User,
        limit: int = 50,
    ) -> list[ManualReviewItemResponse]:
        """Fetch records requiring manual attention or overrides."""
        uni_id = user.university_id
        stmt = (
            select(AttendanceRecord)
            .join(AttendanceSession, AttendanceRecord.attendance_session_id == AttendanceSession.id)
            .options(
                joinedload(AttendanceRecord.student).joinedload(Student.user),
                joinedload(AttendanceRecord.session)
                .joinedload(AttendanceSession.class_occurrence)
                .joinedload(ClassOccurrence.course_offering)
                .joinedload(CourseOffering.course),
            )
            .where(
                AttendanceSession.university_id == uni_id,
                AttendanceRecord.is_manual == True,  # noqa: E712
            )
            .order_by(desc(AttendanceRecord.updated_at))
            .limit(limit)
        )
        res = await db.execute(stmt)
        records = list(res.unique().scalars().all())

        items: list[ManualReviewItemResponse] = []
        for rec in records:
            student = rec.student
            stu_user = student.user if student else None
            stu_name = (
                stu_user.username if stu_user else (student.student_number if student else None)
            )
            stu_num = student.student_number if student else None

            session = rec.session
            occ = session.class_occurrence if session else None
            offering = occ.course_offering if occ else None
            course = offering.course if offering else None
            c_code = course.code if course else None
            c_title = course.name if course else None

            items.append(
                ManualReviewItemResponse(
                    record_id=rec.id,
                    session_id=rec.attendance_session_id,
                    student_id=rec.student_id,
                    student_name=stu_name,
                    student_number=stu_num,
                    course_code=c_code,
                    course_title=c_title,
                    status=rec.status,
                    attendance_credit=float(rec.attendance_credit),
                    verification_method="MANUAL" if rec.is_manual else None,
                    is_flagged=rec.is_manual,
                    flag_reasons=[rec.manual_reason] if rec.manual_reason else [],
                    is_manual=rec.is_manual,
                    created_at=rec.created_at,
                )
            )
        return items

    @staticmethod
    async def confirm_manual_review(
        db: AsyncSession,
        user: User,
        record_id: uuid.UUID,
        dto: ManualReviewConfirmRequest,
    ) -> AttendanceRecord:
        """Confirm or adjust a record under manual review, appending an audit revision."""
        rec_stmt = (
            select(AttendanceRecord).where(AttendanceRecord.id == record_id).with_for_update()
        )
        rec_res = await db.execute(rec_stmt)
        record = rec_res.scalar_one_or_none()
        if not record:
            raise NotFoundException("AttendanceRecord", record_id)

        session = await db.get(AttendanceSession, record.attendance_session_id)
        if not session:
            raise NotFoundException("AttendanceSession", record.attendance_session_id)

        await AttendanceOperationsService.verify_reviewer_scope(db, user, session)

        now = utc_now()
        prev_status = record.status
        prev_credit = float(record.attendance_credit)

        policy_snapshot = session.policy_snapshot or {}
        status_credit_map = policy_snapshot.get("status_credit", DEFAULT_STATUS_CREDIT)

        if dto.target_credit is not None:
            calculated_credit = dto.target_credit
        elif dto.target_status.value in status_credit_map:
            calculated_credit = float(status_credit_map[dto.target_status.value])
        elif dto.target_status == AttendanceStatus.PRESENT:
            calculated_credit = 1.0
        elif dto.target_status == AttendanceStatus.LATE:
            calculated_credit = 0.5
        elif dto.target_status == AttendanceStatus.EXCUSED:
            calculated_credit = float(policy_snapshot.get("excused_credit", 0.0))
        elif dto.target_status == AttendanceStatus.LEAVE:
            calculated_credit = 0.0
        else:
            calculated_credit = 0.0

        record.status = dto.target_status.value
        record.attendance_credit = calculated_credit
        record.is_manual = True
        record.manual_reason = f"Manual review confirmed: {dto.reason.strip()}"
        record.version_no += 1
        record.finalized_at_utc = now

        revision = AttendanceRevision(
            attendance_session_id=session.id,
            attendance_record_id=record.id,
            actor_user_id=user.id,
            event_type=AttendanceAuditEventType.ADMIN_OVERRIDE.value,
            previous_status=prev_status,
            new_status=dto.target_status.value,
            previous_credit=prev_credit,
            new_credit=calculated_credit,
            reason=f"Manual review confirmed: {dto.reason.strip()}",
            metadata_json={"reviewer_user_id": str(user.id)},
            occurred_at_utc=now,
        )
        db.add(revision)

        await db.commit()
        await db.refresh(record)
        return record
