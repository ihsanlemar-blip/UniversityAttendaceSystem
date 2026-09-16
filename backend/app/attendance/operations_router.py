"""API Router for Attendance Operations, Corrections, Excuses, Leave, and Revisions."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.attendance.operations_schemas import (
    AdminOverrideRequest,
    CorrectionRequestCreate,
    CorrectionRequestResponse,
    CorrectionRequestReview,
    ExcuseRequestCreate,
    ExcuseRequestResponse,
    ExcuseRequestReview,
    LeaveRequestCreate,
    LeaveRequestResponse,
    LeaveRequestReview,
    RecordTimelineResponse,
    RevisionReversalRequest,
)
from backend.app.attendance.operations_service import AttendanceOperationsService
from backend.app.attendance.schemas import AttendanceRecordResponse
from backend.app.common.schemas import StandardResponse
from backend.app.core.constants import CorrectionRequestStatus, PermissionCode
from backend.app.core.database import get_db_session
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_permission

router = APIRouter(prefix="/attendance/operations", tags=["Attendance Operations & Workflows"])


# =============================================================================
# 1. Student Correction Requests
# =============================================================================


@router.post(
    "/corrections",
    response_model=StandardResponse[CorrectionRequestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit Student Attendance Correction Request",
    description=(
        "Allows enrolled student to submit a correction request for their "
        "own record within the session window."
    ),
)
async def submit_correction_request(
    dto: CorrectionRequestCreate,
    user: Annotated[
        User, Depends(require_permission(PermissionCode.ATTENDANCE_CORRECTIONS_REQUEST))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CorrectionRequestResponse]:
    req = await AttendanceOperationsService.submit_correction_request(db, user, dto)
    return StandardResponse(
        data=CorrectionRequestResponse.model_validate(req),
        meta={"message": "Correction request submitted successfully."},
    )


@router.get(
    "/corrections/my",
    response_model=StandardResponse[list[CorrectionRequestResponse]],
    summary="List Current Student's Correction Requests",
    description="Returns all correction requests submitted by the currently authenticated student.",
)
async def list_my_correction_requests(
    user: Annotated[
        User, Depends(require_permission(PermissionCode.ATTENDANCE_CORRECTIONS_REQUEST))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[list[CorrectionRequestResponse]]:
    requests = await AttendanceOperationsService.get_student_correction_requests(db, user)
    return StandardResponse(
        data=[CorrectionRequestResponse.model_validate(r) for r in requests],
    )


@router.post(
    "/corrections/{request_id}/cancel",
    response_model=StandardResponse[CorrectionRequestResponse],
    summary="Cancel Pending Correction Request",
    description=(
        "Allows student to cancel their own pending correction request before review begins."
    ),
)
async def cancel_correction_request(
    request_id: uuid.UUID,
    user: Annotated[
        User, Depends(require_permission(PermissionCode.ATTENDANCE_CORRECTIONS_REQUEST))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CorrectionRequestResponse]:
    req = await AttendanceOperationsService.cancel_correction_request(db, user, request_id)
    return StandardResponse(
        data=CorrectionRequestResponse.model_validate(req),
        meta={"message": "Correction request cancelled."},
    )


# =============================================================================
# 2. Reviewer Correction Queue & Actions
# =============================================================================


@router.get(
    "/corrections/queue",
    response_model=StandardResponse[list[CorrectionRequestResponse]],
    summary="List Reviewer Correction Queue",
    description="Fetches reviewable correction requests for lecturers and administrators.",
)
async def get_correction_queue(
    user: Annotated[
        User, Depends(require_permission(PermissionCode.ATTENDANCE_CORRECTIONS_REVIEW))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    status_filter: Annotated[
        CorrectionRequestStatus | None,
        Query(description="Filter by status (e.g. PENDING)"),
    ] = None,
) -> StandardResponse[list[CorrectionRequestResponse]]:
    requests = await AttendanceOperationsService.get_reviewer_queue(db, user, status_filter)
    return StandardResponse(
        data=[CorrectionRequestResponse.model_validate(r) for r in requests],
    )


@router.post(
    "/corrections/{request_id}/review",
    response_model=StandardResponse[CorrectionRequestResponse],
    summary="Review Correction Request (Approve / Reject)",
    description=(
        "Authorized lecturer or administrator reviews a correction request, "
        "appending an immutable revision."
    ),
)
async def review_correction_request(
    request_id: uuid.UUID,
    dto: CorrectionRequestReview,
    user: Annotated[
        User, Depends(require_permission(PermissionCode.ATTENDANCE_CORRECTIONS_REVIEW))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CorrectionRequestResponse]:
    req = await AttendanceOperationsService.review_correction_request(db, user, request_id, dto)
    return StandardResponse(
        data=CorrectionRequestResponse.model_validate(req),
        meta={"message": f"Correction request {dto.status.value.lower()}."},
    )


# =============================================================================
# 3. Direct / Emergency Overrides & Reversals (INV-08, INV-06)
# =============================================================================


@router.post(
    "/overrides",
    response_model=StandardResponse[AttendanceRecordResponse],
    summary="Direct / Emergency Attendance Override",
    description="Authorized lecturer or administrator overrides attendance record status directly.",
)
async def override_attendance_record(
    dto: AdminOverrideRequest,
    user: Annotated[
        User, Depends(require_permission(PermissionCode.ATTENDANCE_CORRECTIONS_OVERRIDE))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceRecordResponse]:
    record = await AttendanceOperationsService.admin_override(db, user, dto)
    return StandardResponse(
        data=AttendanceRecordResponse.model_validate(record),
        meta={"message": "Attendance record overridden successfully."},
    )


@router.post(
    "/reversals",
    response_model=StandardResponse[AttendanceRecordResponse],
    summary="Reverse Prior Revision Compensating Transaction",
    description=(
        "Creates a compensating revision to reverse a prior action without erasing history."
    ),
)
async def reverse_prior_revision(
    dto: RevisionReversalRequest,
    user: Annotated[
        User, Depends(require_permission(PermissionCode.ATTENDANCE_CORRECTIONS_REVIEW))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceRecordResponse]:
    record = await AttendanceOperationsService.reverse_revision(db, user, dto)
    return StandardResponse(
        data=AttendanceRecordResponse.model_validate(record),
        meta={"message": "Prior revision reversed via compensating revision."},
    )


# =============================================================================
# 4. Absence Excuse Workflows
# =============================================================================


@router.post(
    "/excuses",
    response_model=StandardResponse[ExcuseRequestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit Absence Excuse Request",
    description="Submit an official excuse (medical, official activity, emergency) for absence.",
)
async def submit_excuse_request(
    dto: ExcuseRequestCreate,
    user: Annotated[User, Depends(require_permission(PermissionCode.ATTENDANCE_EXCUSES_REQUEST))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[ExcuseRequestResponse]:
    req = await AttendanceOperationsService.submit_excuse_request(db, user, dto)
    return StandardResponse(
        data=ExcuseRequestResponse.model_validate(req),
        meta={"message": "Absence excuse request submitted successfully."},
    )


@router.post(
    "/excuses/{request_id}/review",
    response_model=StandardResponse[ExcuseRequestResponse],
    summary="Review Absence Excuse Request",
    description="Authorized reviewer approves or rejects an absence excuse request.",
)
async def review_excuse_request(
    request_id: uuid.UUID,
    dto: ExcuseRequestReview,
    user: Annotated[User, Depends(require_permission(PermissionCode.ATTENDANCE_EXCUSES_REVIEW))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[ExcuseRequestResponse]:
    req = await AttendanceOperationsService.review_excuse_request(db, user, request_id, dto)
    return StandardResponse(
        data=ExcuseRequestResponse.model_validate(req),
        meta={"message": f"Excuse request {dto.status.value.lower()}."},
    )


# =============================================================================
# 5. Pre-Class Leave Workflows (Section 35-38)
# =============================================================================


@router.post(
    "/leave",
    response_model=StandardResponse[LeaveRequestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit Pre-Class Leave Request",
    description="Student submits a pre-class leave request for a scheduled class occurrence.",
)
async def submit_leave_request(
    dto: LeaveRequestCreate,
    user: Annotated[User, Depends(require_permission(PermissionCode.ATTENDANCE_LEAVE_REQUEST))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[LeaveRequestResponse]:
    req = await AttendanceOperationsService.submit_leave_request(db, user, dto)
    return StandardResponse(
        data=LeaveRequestResponse.model_validate(req),
        meta={"message": "Leave request submitted successfully."},
    )


@router.post(
    "/leave/{request_id}/review",
    response_model=StandardResponse[LeaveRequestResponse],
    summary="Review Pre-Class Leave Request",
    description="Review pre-class leave request (approved LEAVE grants 0 attendance credit).",
)
async def review_leave_request(
    request_id: uuid.UUID,
    dto: LeaveRequestReview,
    user: Annotated[User, Depends(require_permission(PermissionCode.ATTENDANCE_LEAVE_REVIEW))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[LeaveRequestResponse]:
    req = await AttendanceOperationsService.review_leave_request(db, user, request_id, dto)
    return StandardResponse(
        data=LeaveRequestResponse.model_validate(req),
        meta={"message": f"Leave request {dto.status.value.lower()}."},
    )


# =============================================================================
# 6. Audit Revision Timeline (INV-06)
# =============================================================================


@router.get(
    "/records/{record_id}/timeline",
    response_model=StandardResponse[RecordTimelineResponse],
    summary="Get Attendance Record Immutable Revision Timeline",
    description="Retrieves the complete audit history and revision chain for an attendance record.",
)
async def get_record_timeline(
    record_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(PermissionCode.ATTENDANCE_AUDIT_READ))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[RecordTimelineResponse]:
    timeline = await AttendanceOperationsService.get_record_timeline(db, record_id)
    return StandardResponse(
        data=timeline,
    )
