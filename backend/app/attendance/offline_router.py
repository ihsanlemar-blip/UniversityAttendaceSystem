"""API Router for Milestone 12: Offline Attendance, Signed Offline Authority & Reconciliation."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.attendance.offline_schemas import (
    OfflineConflictResolveRequest,
    OfflineConflictResponse,
    OfflineHostSyncRequest,
    OfflineHostSyncResponse,
    OfflinePermitRequest,
    OfflinePermitResponse,
    OfflineStudentSyncRequest,
    OfflineStudentSyncResponse,
    OfflineVerificationKeyResponse,
)
from backend.app.attendance.offline_service import OfflineAttendanceService
from backend.app.attendance.service import AttendanceService
from backend.app.auth.dependencies import get_current_user
from backend.app.common.schemas import StandardResponse
from backend.app.common.types import utc_now
from backend.app.core.constants import EvidenceSourceMode, PermissionCode
from backend.app.core.database import get_db_session
from backend.app.core.exceptions import NotFoundException
from backend.app.models.offline_attendance import OfflineSyncConflict
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_permission

router = APIRouter(prefix="/offline", tags=["Offline Attendance"])


@router.get(
    "/verification-keys",
    response_model=StandardResponse[OfflineVerificationKeyResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Server Verification Public Keys",
)
async def get_offline_verification_keys(
    current_user: Annotated[User, Depends(get_current_user)],
) -> StandardResponse[OfflineVerificationKeyResponse]:
    """Retrieve backend Ed25519 public key used to verify offline permits."""
    keys = OfflineAttendanceService.get_verification_keys()
    return StandardResponse(
        data=keys,
        meta={"message": "Offline verification public keys retrieved."},
    )


@router.post(
    "/permits/request",
    response_model=StandardResponse[OfflinePermitResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Request Signed Offline Attendance Permit",
)
async def request_offline_permit(
    payload: OfflinePermitRequest,
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.ATTENDANCE_SESSIONS_MANAGE.value)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[OfflinePermitResponse]:
    """Issue a cryptographically signed OfflineAttendancePermit for a class session."""
    permit = await OfflineAttendanceService.issue_offline_permit(
        db=db,
        current_user=current_user,
        request=payload,
    )
    return StandardResponse(
        data=permit,
        meta={"message": "Offline attendance permit issued successfully."},
    )


@router.post(
    "/sync/host-events",
    response_model=StandardResponse[OfflineHostSyncResponse],
    status_code=status.HTTP_200_OK,
    summary="Synchronize Lecturer Offline Host Event Chain",
)
async def sync_host_events(
    payload: OfflineHostSyncRequest,
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.ATTENDANCE_SESSIONS_MANAGE.value)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[OfflineHostSyncResponse]:
    """Ingest lecturer offline event hash-chain and trigger claim reconciliation."""
    response = await OfflineAttendanceService.sync_host_events(
        db=db,
        current_user=current_user,
        payload=payload,
    )
    return StandardResponse(
        data=response,
        meta={"message": "Host event chain synchronized and reconciled."},
    )


@router.post(
    "/sync/student-claims",
    response_model=StandardResponse[OfflineStudentSyncResponse],
    status_code=status.HTTP_200_OK,
    summary="Synchronize Student Offline Attendance Claims",
)
async def sync_student_claims(
    payload: OfflineStudentSyncRequest,
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.ATTENDANCE_SELF_READ.value)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[OfflineStudentSyncResponse]:
    """Submit local student attendance claims for verification and reconciliation."""
    response = await OfflineAttendanceService.sync_student_claims(
        db=db,
        current_user=current_user,
        payload=payload,
    )
    return StandardResponse(
        data=response,
        meta={"message": "Student claims synchronized successfully."},
    )


@router.get(
    "/conflicts",
    response_model=StandardResponse[list[OfflineConflictResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Unresolved Offline Sync Conflicts",
)
async def list_offline_conflicts(
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.ATTENDANCE_RECORDS_OVERRIDE.value)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session_id: Annotated[uuid.UUID | None, Query()] = None,
) -> StandardResponse[list[OfflineConflictResponse]]:
    """List offline sync conflicts requiring administrative review."""
    stmt = select(OfflineSyncConflict).order_by(OfflineSyncConflict.created_at.desc())
    if session_id:
        stmt = stmt.where(OfflineSyncConflict.attendance_session_id == session_id)

    res = await db.execute(stmt)
    conflicts = list(res.scalars().all())

    items = [
        OfflineConflictResponse(
            id=c.id,
            attendance_session_id=c.attendance_session_id,
            offline_permit_id=c.offline_permit_id,
            student_id=c.student_id,
            conflict_type=c.conflict_type,
            resolution_status=c.resolution_status,
            conflict_details=c.conflict_details,
            created_at=c.created_at,
        )
        for c in conflicts
    ]
    return StandardResponse(
        data=items,
        meta={"message": "Offline sync conflicts retrieved."},
    )


@router.post(
    "/conflicts/{conflict_id}/resolve",
    response_model=StandardResponse[OfflineConflictResponse],
    status_code=status.HTTP_200_OK,
    summary="Resolve Offline Synchronization Conflict",
)
async def resolve_offline_conflict(
    conflict_id: uuid.UUID,
    payload: OfflineConflictResolveRequest,
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.ATTENDANCE_RECORDS_OVERRIDE.value)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[OfflineConflictResponse]:
    """Manually resolve an offline conflict with audit trail and optional checkpoint credit."""
    stmt = select(OfflineSyncConflict).where(OfflineSyncConflict.id == conflict_id)
    res = await db.execute(stmt)
    conflict = res.scalar_one_or_none()
    if not conflict:
        raise NotFoundException("OfflineSyncConflict", conflict_id)

    conflict.resolution_status = payload.resolution_status
    conflict.resolution_notes = payload.resolution_notes
    conflict.resolved_by_user_id = current_user.id
    conflict.resolved_at_utc = utc_now()

    if payload.credit_checkpoint and conflict.student_id and payload.checkpoint_type:
        await AttendanceService.record_verified_checkpoint_credit(
            db=db,
            session_id=conflict.attendance_session_id,
            checkpoint_type=payload.checkpoint_type,
            student_id=conflict.student_id,
            actor_id=current_user.id,
            source_mode=EvidenceSourceMode.MANUAL.value,
            reason=f"Manual offline conflict resolution: {payload.resolution_notes}",
            is_real_time=False,
        )

    await db.commit()
    await db.refresh(conflict)

    return StandardResponse(
        data=OfflineConflictResponse(
            id=conflict.id,
            attendance_session_id=conflict.attendance_session_id,
            offline_permit_id=conflict.offline_permit_id,
            student_id=conflict.student_id,
            conflict_type=conflict.conflict_type,
            resolution_status=conflict.resolution_status,
            conflict_details=conflict.conflict_details,
            created_at=conflict.created_at,
        ),
        meta={"message": "Conflict resolved successfully."},
    )
