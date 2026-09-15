"""API Router for Attendance Policies, Sessions, Checkpoints, Roster Records, and Audit."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.attendance.schemas import (
    AttendanceCheckpointResponse,
    AttendancePolicyCreateRequest,
    AttendancePolicyResponse,
    AttendancePolicyUpdateRequest,
    AttendanceRecordOverrideRequest,
    AttendanceRecordResponse,
    AttendanceRevisionResponse,
    AttendanceSessionCreateRequest,
    AttendanceSessionDetailResponse,
    AttendanceSessionResponse,
    BleAdvertisementResponse,
    CheckpointCreditResponse,
    CheckpointOpenRequest,
    ManualCheckpointCreditRequest,
    PresenceCheckInRequest,
    PresenceCheckInResponse,
    QrCheckInRequest,
    QrCheckInResponse,
    QrTokenResponse,
    StudentAttendanceSelfResponse,
)
from backend.app.attendance.service import AttendanceService
from backend.app.common.schemas import StandardResponse
from backend.app.core.constants import AttendanceStatus, SystemRole
from backend.app.core.database import get_db_session
from backend.app.core.exceptions import DomainException, NotFoundException
from backend.app.models.attendance_checkpoint import AttendanceCheckpoint
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.class_occurrence import ClassOccurrence
from backend.app.models.course_offering import CourseOffering
from backend.app.models.lecturer import Lecturer
from backend.app.models.lecturer_assignment import LecturerAssignment
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_permission
from backend.app.rbac.service import RbacService

router = APIRouter(prefix="/attendance", tags=["Attendance Core Engine"])
students_router = APIRouter(prefix="/students", tags=["Student Attendance Self-Service"])


# ==========================================
# Authorization Helper
# ==========================================


async def _verify_occurrence_authority(
    db: AsyncSession,
    current_user: User,
    occurrence: ClassOccurrence,
    permission_code: str,
) -> None:
    """Verify current user has authority over a class occurrence:

    1. Super Admin / University Admin via university-level permission.
    2. Faculty / Department Admin via academic unit hierarchy permission.
    3. Assigned Primary Lecturer, Substitute Lecturer, or Co-Teacher.
    """
    user_roles = set(await RbacService.get_user_roles(db, current_user.id))

    # 1. Global university-level admin permission
    admin_roles = {
        SystemRole.SUPER_ADMIN.value,
        SystemRole.UNIVERSITY_ADMIN.value,
        SystemRole.ATTENDANCE_OFFICER.value,
    }
    if user_roles & admin_roles:
        if await RbacService.has_permission(
            db=db,
            user_id=current_user.id,
            permission_code=permission_code,
            university_id=current_user.university_id,
            allow_scoped=False,
        ):
            return

    # 2. Academic unit hierarchy
    offering: CourseOffering | None = None
    if occurrence.course_offering_id:
        offering = await db.get(CourseOffering, occurrence.course_offering_id)

    unit_admin_roles = {
        SystemRole.FACULTY_ADMIN.value,
        SystemRole.DEPARTMENT_ADMIN.value,
    }
    if user_roles & unit_admin_roles:
        unit_id = offering.academic_unit_id if offering else None
        if unit_id and await RbacService.has_academic_unit_permission(
            db=db,
            user_id=current_user.id,
            permission_code=permission_code,
            university_id=current_user.university_id,
            target_unit_id=unit_id,
        ):
            return

    # 3. Lecturer assignment check
    lec_stmt = select(Lecturer).where(Lecturer.user_id == current_user.id)
    lec_res = await db.execute(lec_stmt)
    lecturer = lec_res.scalar_one_or_none()
    if lecturer:
        if (
            occurrence.lecturer_id == lecturer.id
            or occurrence.substitute_lecturer_id == lecturer.id
        ):
            return
        if offering:
            assign_stmt = select(LecturerAssignment).where(
                LecturerAssignment.course_offering_id == offering.id,
                LecturerAssignment.lecturer_id == lecturer.id,
            )
            assign_res = await db.execute(assign_stmt)
            if assign_res.scalar_one_or_none():
                return

    raise DomainException(
        code="PERMISSION_DENIED",
        message="You do not have authorization to manage attendance for this class occurrence.",
        status_code=403,
    )


# ==========================================
# 1. Attendance Policy Endpoints
# ==========================================


@router.post(
    "/policies",
    response_model=StandardResponse[AttendancePolicyResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create attendance policy",
)
async def create_attendance_policy(
    payload: AttendancePolicyCreateRequest,
    current_user: Annotated[
        User, Depends(require_permission("attendance_policies.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendancePolicyResponse]:
    """Create a new attendance policy in the resolution hierarchy."""
    policy = await AttendanceService.create_policy(
        db=db,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=AttendancePolicyResponse.model_validate(policy),
        meta={"message": "Attendance policy created successfully."},
    )


@router.get(
    "/policies",
    response_model=StandardResponse[list[AttendancePolicyResponse]],
    summary="List attendance policies",
)
async def list_attendance_policies(
    current_user: Annotated[
        User, Depends(require_permission("attendance_policies.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    scope_type: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> StandardResponse[list[AttendancePolicyResponse]]:
    """List attendance policies matching scope filters."""
    policies = await AttendanceService.list_policies(
        db=db,
        university_id=current_user.university_id,
        scope_type=scope_type,
        status=status_filter,
    )
    return StandardResponse(
        data=[AttendancePolicyResponse.model_validate(p) for p in policies],
        meta={"message": "Attendance policies retrieved successfully."},
    )


@router.get(
    "/policies/{policy_id}",
    response_model=StandardResponse[AttendancePolicyResponse],
    summary="Get attendance policy by ID",
)
async def get_attendance_policy(
    policy_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("attendance_policies.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendancePolicyResponse]:
    """Retrieve details of a specific attendance policy."""
    policy = await AttendanceService.get_policy(
        db=db,
        policy_id=policy_id,
        university_id=current_user.university_id,
    )
    return StandardResponse(
        data=AttendancePolicyResponse.model_validate(policy),
        meta={"message": "Attendance policy retrieved successfully."},
    )


@router.patch(
    "/policies/{policy_id}",
    response_model=StandardResponse[AttendancePolicyResponse],
    summary="Update attendance policy",
)
async def update_attendance_policy(
    policy_id: uuid.UUID,
    payload: AttendancePolicyUpdateRequest,
    current_user: Annotated[
        User, Depends(require_permission("attendance_policies.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendancePolicyResponse]:
    """Update configurable parameters of an attendance policy."""
    policy = await AttendanceService.update_policy(
        db=db,
        policy_id=policy_id,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=AttendancePolicyResponse.model_validate(policy),
        meta={"message": "Attendance policy updated successfully."},
    )


# ==========================================
# 2. Attendance Session Lifecycle Endpoints
# ==========================================


@router.post(
    "/sessions",
    response_model=StandardResponse[AttendanceSessionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Initialize attendance session",
)
async def initialize_attendance_session(
    payload: AttendanceSessionCreateRequest,
    current_user: Annotated[
        User, Depends(require_permission("attendance_sessions.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceSessionResponse]:
    """Initialize an attendance session anchored 1:1 to a concrete ClassOccurrence."""
    # Verify occurrence and authority
    stmt = (
        select(ClassOccurrence)
        .options(selectinload(ClassOccurrence.course_offering))
        .where(
            ClassOccurrence.id == payload.class_occurrence_id,
            ClassOccurrence.university_id == current_user.university_id,
        )
    )
    res = await db.execute(stmt)
    occurrence = res.scalar_one_or_none()
    if not occurrence:
        raise NotFoundException("ClassOccurrence", payload.class_occurrence_id)

    await _verify_occurrence_authority(
        db=db,
        current_user=current_user,
        occurrence=occurrence,
        permission_code="attendance_sessions.manage",
    )

    session = await AttendanceService.initialize_session(
        db=db,
        university_id=current_user.university_id,
        class_occurrence_id=payload.class_occurrence_id,
        actor_id=current_user.id,
        attendance_policy_id=payload.attendance_policy_id,
        activate_immediately=payload.activate_immediately,
    )
    return StandardResponse(
        data=AttendanceSessionResponse.model_validate(session),
        meta={"message": "Attendance session initialized successfully."},
    )


@router.get(
    "/sessions/{session_id}",
    response_model=StandardResponse[AttendanceSessionDetailResponse],
    summary="Get attendance session details",
)
async def get_attendance_session(
    session_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("attendance_sessions.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceSessionDetailResponse]:
    """Get session details including checkpoints and real-time attendance counts."""
    session = await AttendanceService.get_session(
        db=db,
        session_id=session_id,
        university_id=current_user.university_id,
    )
    # Calculate counts
    records_stmt = select(AttendanceRecord).where(
        AttendanceRecord.attendance_session_id == session.id
    )
    records_res = await db.execute(records_stmt)
    records = records_res.scalars().all()

    detail = AttendanceSessionDetailResponse(
        id=session.id,
        university_id=session.university_id,
        class_occurrence_id=session.class_occurrence_id,
        attendance_policy_id=session.attendance_policy_id,
        policy_snapshot=session.policy_snapshot,
        status=session.status,
        host_type=session.host_type,
        opened_at_utc=session.opened_at_utc,
        paused_at_utc=session.paused_at_utc,
        resumed_at_utc=session.resumed_at_utc,
        closed_at_utc=session.closed_at_utc,
        opened_by_user_id=session.opened_by_user_id,
        closed_by_user_id=session.closed_by_user_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        checkpoints=[AttendanceCheckpointResponse.model_validate(cp) for cp in session.checkpoints],
        total_enrolled=len(records),
        total_present=sum(1 for r in records if r.status == AttendanceStatus.PRESENT.value),
        total_late=sum(1 for r in records if r.status == AttendanceStatus.LATE.value),
        total_absent=sum(1 for r in records if r.status == AttendanceStatus.ABSENT.value),
        total_excused=sum(1 for r in records if r.status == AttendanceStatus.EXCUSED.value),
        total_leave=sum(1 for r in records if r.status == AttendanceStatus.LEAVE.value),
        total_pending=sum(1 for r in records if r.status == AttendanceStatus.PENDING.value),
    )
    return StandardResponse(
        data=detail,
        meta={"message": "Attendance session details retrieved successfully."},
    )


@router.post(
    "/sessions/{session_id}/open",
    response_model=StandardResponse[AttendanceSessionResponse],
    summary="Activate attendance session",
)
async def open_attendance_session(
    session_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("attendance_sessions.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceSessionResponse]:
    """Activate a scheduled attendance session and freeze the course offering roster."""
    session = await AttendanceService.get_session(db, session_id, current_user.university_id)
    occ = await db.get(ClassOccurrence, session.class_occurrence_id)
    if occ:
        await _verify_occurrence_authority(
            db=db,
            current_user=current_user,
            occurrence=occ,
            permission_code="attendance_sessions.manage",
        )

    updated_session = await AttendanceService.open_session(
        db=db,
        session_id=session_id,
        university_id=current_user.university_id,
        actor_id=current_user.id,
    )
    return StandardResponse(
        data=AttendanceSessionResponse.model_validate(updated_session),
        meta={"message": "Attendance session activated successfully."},
    )


@router.post(
    "/sessions/{session_id}/pause",
    response_model=StandardResponse[AttendanceSessionResponse],
    summary="Pause attendance session",
)
async def pause_attendance_session(
    session_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("attendance_sessions.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceSessionResponse]:
    """Pause an active session and close any open checkpoint windows."""
    session = await AttendanceService.get_session(db, session_id, current_user.university_id)
    occ = await db.get(ClassOccurrence, session.class_occurrence_id)
    if occ:
        await _verify_occurrence_authority(
            db=db,
            current_user=current_user,
            occurrence=occ,
            permission_code="attendance_sessions.manage",
        )

    updated_session = await AttendanceService.pause_session(
        db=db,
        session_id=session_id,
        university_id=current_user.university_id,
        actor_id=current_user.id,
    )
    return StandardResponse(
        data=AttendanceSessionResponse.model_validate(updated_session),
        meta={"message": "Attendance session paused successfully."},
    )


@router.post(
    "/sessions/{session_id}/resume",
    response_model=StandardResponse[AttendanceSessionResponse],
    summary="Resume attendance session",
)
async def resume_attendance_session(
    session_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("attendance_sessions.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceSessionResponse]:
    """Resume a paused attendance session."""
    session = await AttendanceService.get_session(db, session_id, current_user.university_id)
    occ = await db.get(ClassOccurrence, session.class_occurrence_id)
    if occ:
        await _verify_occurrence_authority(
            db=db,
            current_user=current_user,
            occurrence=occ,
            permission_code="attendance_sessions.manage",
        )

    updated_session = await AttendanceService.resume_session(
        db=db,
        session_id=session_id,
        university_id=current_user.university_id,
        actor_id=current_user.id,
    )
    return StandardResponse(
        data=AttendanceSessionResponse.model_validate(updated_session),
        meta={"message": "Attendance session resumed successfully."},
    )


@router.post(
    "/sessions/{session_id}/close",
    response_model=StandardResponse[AttendanceSessionResponse],
    summary="Close attendance session",
)
async def close_attendance_session(
    session_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("attendance_sessions.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceSessionResponse]:
    """Close session and run combinatorial 8-pattern attendance evaluation on student records."""
    session = await AttendanceService.get_session(db, session_id, current_user.university_id)
    occ = await db.get(ClassOccurrence, session.class_occurrence_id)
    if occ:
        await _verify_occurrence_authority(
            db=db,
            current_user=current_user,
            occurrence=occ,
            permission_code="attendance_sessions.manage",
        )

    updated_session = await AttendanceService.close_session(
        db=db,
        session_id=session_id,
        university_id=current_user.university_id,
        actor_id=current_user.id,
    )
    return StandardResponse(
        data=AttendanceSessionResponse.model_validate(updated_session),
        meta={"message": "Attendance session closed and records finalized."},
    )


# ==========================================
# 3. Checkpoint Control Endpoints
# ==========================================


@router.post(
    "/sessions/{session_id}/checkpoints/{checkpoint_type}/open",
    response_model=StandardResponse[AttendanceCheckpointResponse],
    summary="Open attendance checkpoint window",
)
async def open_checkpoint_window(
    session_id: uuid.UUID,
    checkpoint_type: str,
    payload: CheckpointOpenRequest,
    current_user: Annotated[
        User, Depends(require_permission("attendance_checkpoints.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceCheckpointResponse]:
    """Open an attendance verification window (START, MIDDLE, or END)."""
    session = await AttendanceService.get_session(db, session_id, current_user.university_id)
    occ = await db.get(ClassOccurrence, session.class_occurrence_id)
    if occ:
        await _verify_occurrence_authority(
            db=db,
            current_user=current_user,
            occurrence=occ,
            permission_code="attendance_checkpoints.manage",
        )

    cp = await AttendanceService.open_checkpoint(
        db=db,
        session_id=session_id,
        checkpoint_type=checkpoint_type.upper(),
        university_id=current_user.university_id,
        actor_id=current_user.id,
        window_duration_seconds=payload.window_duration_seconds,
    )
    return StandardResponse(
        data=AttendanceCheckpointResponse.model_validate(cp),
        meta={"message": f"Checkpoint '{checkpoint_type}' opened successfully."},
    )


@router.post(
    "/sessions/{session_id}/checkpoints/{checkpoint_type}/close",
    response_model=StandardResponse[AttendanceCheckpointResponse],
    summary="Close attendance checkpoint window",
)
async def close_checkpoint_window(
    session_id: uuid.UUID,
    checkpoint_type: str,
    current_user: Annotated[
        User, Depends(require_permission("attendance_checkpoints.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceCheckpointResponse]:
    """Close an attendance verification window."""
    session = await AttendanceService.get_session(db, session_id, current_user.university_id)
    occ = await db.get(ClassOccurrence, session.class_occurrence_id)
    if occ:
        await _verify_occurrence_authority(
            db=db,
            current_user=current_user,
            occurrence=occ,
            permission_code="attendance_checkpoints.manage",
        )

    cp = await AttendanceService.close_checkpoint(
        db=db,
        session_id=session_id,
        checkpoint_type=checkpoint_type.upper(),
        university_id=current_user.university_id,
        actor_id=current_user.id,
    )
    return StandardResponse(
        data=AttendanceCheckpointResponse.model_validate(cp),
        meta={"message": f"Checkpoint '{checkpoint_type}' closed successfully."},
    )


# ==========================================
# Dynamic QR Presence Verification Endpoints (Milestone 10)
# ==========================================


@router.get(
    "/checkpoints/{checkpoint_id}/qr-token",
    response_model=StandardResponse[QrTokenResponse],
    summary="Get dynamic QR presence token for active checkpoint",
)
async def get_checkpoint_qr_token(
    checkpoint_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("attendance_checkpoints.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    response: Response,
) -> StandardResponse[QrTokenResponse]:
    """Retrieve cryptographically signed dynamic QR token for projector display.

    Returns the current rotating token for the open checkpoint window.
    Disables caching (Cache-Control: no-store).
    """
    stmt = (
        select(AttendanceCheckpoint)
        .join(
            AttendanceSession,
            AttendanceSession.id == AttendanceCheckpoint.attendance_session_id,
        )
        .where(
            AttendanceCheckpoint.id == checkpoint_id,
            AttendanceSession.university_id == current_user.university_id,
        )
    )
    res = await db.execute(stmt)
    cp = res.scalar_one_or_none()
    if not cp:
        raise NotFoundException("AttendanceCheckpoint", checkpoint_id)

    session = await AttendanceService.get_session(
        db, cp.attendance_session_id, current_user.university_id
    )
    occ = await db.get(ClassOccurrence, session.class_occurrence_id)
    if occ:
        await _verify_occurrence_authority(
            db=db,
            current_user=current_user,
            occurrence=occ,
            permission_code="attendance_checkpoints.manage",
        )

    qr_data = await AttendanceService.generate_checkpoint_qr_token(
        db=db,
        checkpoint_id=checkpoint_id,
        university_id=current_user.university_id,
        actor_id=current_user.id,
    )

    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"

    return StandardResponse(
        data=qr_data,
        meta={"message": "Dynamic QR token generated successfully."},
    )


@router.get(
    "/checkpoints/{checkpoint_id}/ble-advertisement",
    response_model=StandardResponse[BleAdvertisementResponse],
    summary="Fetch current compact BLE advertisement payload for an active checkpoint",
)
async def get_checkpoint_ble_advertisement(
    checkpoint_id: uuid.UUID,
    response: Response,
    current_user: Annotated[
        User, Depends(require_permission("attendance_checkpoints.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[BleAdvertisementResponse]:
    """Fetch current ephemeral BLE presence payload for classroom mobile broadcasting.

    Restricted to assigned lecturers and authorized departmental/faculty administrators.
    Students cannot access this endpoint.
    """
    stmt = (
        select(AttendanceCheckpoint)
        .join(
            AttendanceSession,
            AttendanceSession.id == AttendanceCheckpoint.attendance_session_id,
        )
        .where(
            AttendanceCheckpoint.id == checkpoint_id,
            AttendanceSession.university_id == current_user.university_id,
        )
    )
    res = await db.execute(stmt)
    cp = res.scalar_one_or_none()
    if not cp:
        raise NotFoundException("AttendanceCheckpoint", checkpoint_id)

    session = await AttendanceService.get_session(
        db, cp.attendance_session_id, current_user.university_id
    )
    occ = await db.get(ClassOccurrence, session.class_occurrence_id)
    if occ:
        await _verify_occurrence_authority(
            db=db,
            current_user=current_user,
            occurrence=occ,
            permission_code="attendance_checkpoints.manage",
        )

    ble_data = await AttendanceService.generate_checkpoint_ble_advertisement(
        db=db,
        checkpoint_id=checkpoint_id,
        university_id=current_user.university_id,
        actor_id=current_user.id,
    )

    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"

    return StandardResponse(
        data=ble_data,
        meta={"message": "BLE presence advertisement payload generated successfully."},
    )


@router.post(
    "/presence/check-in",
    response_model=StandardResponse[PresenceCheckInResponse],
    summary="Unified student presence check-in (dynamic QR + BLE proximity)",
)
async def student_presence_checkin(
    payload: PresenceCheckInRequest,
    current_user: Annotated[
        User, Depends(require_permission("attendance.self_read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[PresenceCheckInResponse]:
    """Self-service unified presence check-in for enrolled students.

    Supports single-factor (QR_ONLY) and dual-factor (QR_AND_BLE) presence evaluation.
    Student identity is derived strictly from the authenticated user context (INV-01).
    """
    result = await AttendanceService.verify_presence_checkin(
        db=db,
        current_user=current_user,
        qr_token=payload.qr_token,
        ble_observation=payload.ble_observation,
    )
    factors_str = ", ".join(result.verified_factors)
    msg = (
        f"Checkpoint '{result.checkpoint_type}' already credited."
        if result.already_credited
        else f"Checkpoint '{result.checkpoint_type}' presence verified via {factors_str}."
    )
    return StandardResponse(
        data=result,
        meta={"message": msg},
    )


@router.post(
    "/qr/check-in",
    response_model=StandardResponse[QrCheckInResponse],
    summary="Student dynamic QR check-in",
)
async def student_qr_checkin(
    payload: QrCheckInRequest,
    current_user: Annotated[
        User, Depends(require_permission("attendance.self_read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[QrCheckInResponse]:
    """Self-service dynamic QR attendance check-in for enrolled students.

    Student identity is derived strictly from the authenticated current user context (INV-01).
    """
    result = await AttendanceService.verify_qr_checkin(
        db=db,
        token=payload.token,
        current_user=current_user,
    )
    msg = (
        f"Checkpoint '{result.checkpoint_type}' already credited."
        if result.already_credited
        else f"Checkpoint '{result.checkpoint_type}' credited successfully."
    )
    return StandardResponse(
        data=result,
        meta={"message": msg},
    )


@router.post(
    "/sessions/{session_id}/checkpoints/{checkpoint_type}/manual-credit",
    response_model=StandardResponse[CheckpointCreditResponse],
    summary="Record manual checkpoint credit",
)
async def record_manual_checkpoint_credit(
    session_id: uuid.UUID,
    checkpoint_type: str,
    payload: ManualCheckpointCreditRequest,
    current_user: Annotated[
        User, Depends(require_permission("attendance_records.override", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CheckpointCreditResponse]:
    """Record manual checkpoint credit with mandatory justification (INV-08)."""
    session = await AttendanceService.get_session(db, session_id, current_user.university_id)
    occ = await db.get(ClassOccurrence, session.class_occurrence_id)
    if occ:
        await _verify_occurrence_authority(
            db=db,
            current_user=current_user,
            occurrence=occ,
            permission_code="attendance_records.override",
        )

    evidence = await AttendanceService.record_verified_checkpoint_credit(
        db=db,
        session_id=session_id,
        checkpoint_type=checkpoint_type.upper(),
        student_id=payload.student_id,
        actor_id=current_user.id,
        source_mode=payload.source_mode.value,
        reason=payload.reason,
        is_real_time=False,
    )
    return StandardResponse(
        data=CheckpointCreditResponse(
            checkpoint_id=evidence.attendance_checkpoint_id,
            student_id=evidence.student_id,
            checkpoint_type=checkpoint_type.upper(),
            verified=True,
            source_mode=evidence.source_mode,
            server_received_at_utc=evidence.server_received_at_utc,
        ),
        meta={"message": "Checkpoint credit recorded successfully."},
    )


# ==========================================
# 4. Attendance Records & Roster Endpoints
# ==========================================


@router.get(
    "/sessions/{session_id}/records",
    response_model=StandardResponse[list[AttendanceRecordResponse]],
    summary="Get session attendance records roster",
)
async def get_session_attendance_records(
    session_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("attendance_records.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[list[AttendanceRecordResponse]]:
    """Retrieve the complete attendance record sheet for a session."""
    session = await AttendanceService.get_session(db, session_id, current_user.university_id)
    occ = await db.get(ClassOccurrence, session.class_occurrence_id)
    if occ:
        await _verify_occurrence_authority(
            db=db,
            current_user=current_user,
            occurrence=occ,
            permission_code="attendance_records.read",
        )

    records = await AttendanceService.get_session_records(
        db=db,
        session_id=session_id,
        university_id=current_user.university_id,
    )
    return StandardResponse(
        data=[AttendanceRecordResponse.model_validate(r) for r in records],
        meta={"message": "Session attendance records retrieved successfully."},
    )


@router.post(
    "/records/{record_id}/override",
    response_model=StandardResponse[AttendanceRecordResponse],
    summary="Manual attendance record override",
)
async def override_attendance_record(
    record_id: uuid.UUID,
    payload: AttendanceRecordOverrideRequest,
    current_user: Annotated[
        User, Depends(require_permission("attendance_records.override", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceRecordResponse]:
    """Manually override student attendance record with mandatory justification (INV-06, INV-08)."""
    # Fetch record and verify authority
    rec = await db.get(AttendanceRecord, record_id)
    if not rec:
        raise NotFoundException("AttendanceRecord", record_id)

    session = await AttendanceService.get_session(
        db, rec.attendance_session_id, current_user.university_id
    )
    occ = await db.get(ClassOccurrence, session.class_occurrence_id)
    if occ:
        await _verify_occurrence_authority(
            db=db,
            current_user=current_user,
            occurrence=occ,
            permission_code="attendance_records.override",
        )

    record = await AttendanceService.override_record_status(
        db=db,
        record_id=record_id,
        actor_id=current_user.id,
        target_status=payload.status,
        reason=payload.reason,
        new_credit=payload.attendance_credit,
    )
    return StandardResponse(
        data=AttendanceRecordResponse.model_validate(record),
        meta={"message": f"Attendance record status overridden to {payload.status.value}."},
    )


# ==========================================
# 5. Student Self-Service Endpoint
# ==========================================


@students_router.get(
    "/me/attendance",
    response_model=StandardResponse[list[StudentAttendanceSelfResponse]],
    summary="Student personal attendance history",
)
async def get_my_attendance_history(
    current_user: Annotated[
        User, Depends(require_permission("attendance.self_read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[list[StudentAttendanceSelfResponse]]:
    """Enrolled student self-service endpoint to view their own attendance history."""
    # Find student profile for current user
    stmt = select(Student).where(Student.user_id == current_user.id)
    res = await db.execute(stmt)
    student = res.scalar_one_or_none()
    if not student:
        raise DomainException(
            code="STUDENT_PROFILE_REQUIRED",
            message="Authenticated user does not possess an active student profile.",
            status_code=403,
        )

    history = await AttendanceService.get_student_attendance_history(
        db=db,
        student_id=student.id,
    )
    return StandardResponse(
        data=[StudentAttendanceSelfResponse(**item) for item in history],
        meta={"message": "Personal attendance history retrieved successfully."},
    )


# ==========================================
# 6. Audit Revision Ledger Endpoint
# ==========================================


@router.get(
    "/audit",
    response_model=StandardResponse[list[AttendanceRevisionResponse]],
    summary="View attendance audit revision ledger",
)
async def get_attendance_audit_log(
    current_user: Annotated[
        User, Depends(require_permission("attendance_audit.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session_id: Annotated[uuid.UUID | None, Query()] = None,
    record_id: Annotated[uuid.UUID | None, Query()] = None,
) -> StandardResponse[list[AttendanceRevisionResponse]]:
    """Retrieve immutable audit revision records for sessions or student records."""
    revisions = await AttendanceService.get_attendance_audit_log(
        db=db,
        session_id=session_id,
        record_id=record_id,
    )
    return StandardResponse(
        data=[AttendanceRevisionResponse.model_validate(rev) for rev in revisions],
        meta={"message": "Attendance audit revisions retrieved successfully."},
    )
