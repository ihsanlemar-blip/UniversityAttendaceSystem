"""API Router for Milestone 13: Student Device Registration & Primary Device Trust."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.schemas import StandardResponse
from backend.app.core.database import get_db_session
from backend.app.devices.schemas import (
    DeviceRegistrationChallengeRequest,
    DeviceRegistrationChallengeResponse,
    DeviceRegistrationConfirmRequest,
    DeviceReplacementCreateRequest,
    DeviceReplacementResponse,
    DeviceReplacementReviewRequest,
    DeviceStatusUpdateRequest,
    DeviceTrustEventResponse,
    StudentDeviceStatusResponse,
    TrustedDeviceResponse,
)
from backend.app.devices.service import DeviceTrustService
from backend.app.models.trusted_device import (
    DeviceReplacementRequest,
    DeviceTrustEvent,
    TrustedDevice,
)
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_permission
from backend.app.security.rate_limiter import rate_limit

router = APIRouter(prefix="/devices", tags=["Student Devices & Trust"])


# =============================================================================
# 1. Student Self-Service Endpoints
# =============================================================================


@router.get(
    "/me",
    response_model=StandardResponse[StudentDeviceStatusResponse],
    status_code=status.HTTP_200_OK,
    summary="Get current student's registered device and status",
)
async def get_my_device_status(
    current_user: Annotated[
        User, Depends(require_permission("devices.self_read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[StudentDeviceStatusResponse]:
    """Retrieve personal active device information and pending replacement status."""
    device_status = await DeviceTrustService.get_student_device_status(
        db=db, current_user=current_user
    )
    return StandardResponse(
        data=device_status,
        meta={"message": "Personal device status retrieved successfully."},
    )


@router.post(
    "/registration/challenge",
    response_model=StandardResponse[DeviceRegistrationChallengeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Request a device registration challenge",
    dependencies=[Depends(rate_limit("device_challenge", max_requests=10, window_seconds=60))],
)
async def request_registration_challenge(
    payload: DeviceRegistrationChallengeRequest,
    current_user: Annotated[
        User, Depends(require_permission("devices.self_register", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[DeviceRegistrationChallengeResponse]:
    """Issue a short-lived challenge to prove possession of candidate Ed25519 device key."""
    challenge = await DeviceTrustService.request_registration_challenge(
        db=db,
        current_user=current_user,
        payload=payload,
    )
    return StandardResponse(
        data=challenge,
        meta={"message": "Device registration challenge issued."},
    )


@router.post(
    "/registration/confirm",
    response_model=StandardResponse[TrustedDeviceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Confirm initial primary device registration",
)
async def confirm_registration(
    payload: DeviceRegistrationConfirmRequest,
    current_user: Annotated[
        User, Depends(require_permission("devices.self_register", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[TrustedDeviceResponse]:
    """Verify proof of possession and activate primary device for student.

    Requires that student currently has no active registered device.
    """
    device = await DeviceTrustService.confirm_initial_registration(
        db=db,
        current_user=current_user,
        payload=payload,
    )
    return StandardResponse(
        data=device,
        meta={"message": "Primary attendance device activated successfully."},
    )


@router.post(
    "/replacement-requests",
    response_model=StandardResponse[DeviceReplacementResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit a device replacement request",
)
async def create_replacement_request(
    payload: DeviceReplacementCreateRequest,
    current_user: Annotated[
        User, Depends(require_permission("devices.replacement_request", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[DeviceReplacementResponse]:
    """Submit request to replace registered primary device with a new candidate device."""
    request_dto = await DeviceTrustService.request_device_replacement(
        db=db,
        current_user=current_user,
        payload=payload,
    )
    return StandardResponse(
        data=request_dto,
        meta={"message": "Device replacement request submitted and pending administrative review."},
    )


@router.post(
    "/me/lost",
    response_model=StandardResponse[TrustedDeviceResponse],
    status_code=status.HTTP_200_OK,
    summary="Report primary device lost or stolen",
)
async def report_device_lost(
    current_user: Annotated[
        User, Depends(require_permission("devices.replacement_request", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[TrustedDeviceResponse]:
    """Self-suspend current active device upon loss or theft to prevent unauthorized attendance."""
    device_dto = await DeviceTrustService.report_device_lost(db=db, current_user=current_user)
    return StandardResponse(
        data=device_dto,
        meta={"message": "Device marked lost and suspended. Attendance check-in disabled."},
    )


# =============================================================================
# 2. Administrative Review & Management Endpoints
# =============================================================================


@router.get(
    "/replacement-requests",
    response_model=StandardResponse[list[DeviceReplacementResponse]],
    status_code=status.HTTP_200_OK,
    summary="List device replacement requests",
)
async def list_replacement_requests(
    current_user: Annotated[User, Depends(require_permission("devices.read", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> StandardResponse[list[DeviceReplacementResponse]]:
    """List student device replacement requests with optional status filtering."""
    stmt = (
        select(DeviceReplacementRequest)
        .where(DeviceReplacementRequest.university_id == current_user.university_id)
        .order_by(DeviceReplacementRequest.requested_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status_filter:
        stmt = stmt.where(DeviceReplacementRequest.status == status_filter.upper())

    res = await db.execute(stmt)
    records = res.scalars().all()

    items = [DeviceReplacementResponse.model_validate(r) for r in records]
    return StandardResponse(
        data=items,
        meta={"total": len(items), "limit": limit, "offset": offset},
    )


@router.post(
    "/replacement-requests/{request_id}/approve",
    response_model=StandardResponse[DeviceReplacementResponse],
    status_code=status.HTTP_200_OK,
    summary="Approve a device replacement request",
)
async def approve_replacement_request(
    request_id: uuid.UUID,
    payload: DeviceReplacementReviewRequest,
    current_user: Annotated[
        User, Depends(require_permission("devices.replacement_review", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[DeviceReplacementResponse]:
    """Atomically approve device replacement: revoke old device and activate candidate device."""
    approved_dto = await DeviceTrustService.approve_device_replacement(
        db=db,
        request_id=request_id,
        reviewer_user=current_user,
        payload=payload,
    )
    return StandardResponse(
        data=approved_dto,
        meta={"message": "Device replacement approved successfully. Old device replaced."},
    )


@router.post(
    "/replacement-requests/{request_id}/reject",
    response_model=StandardResponse[DeviceReplacementResponse],
    status_code=status.HTTP_200_OK,
    summary="Reject a device replacement request",
)
async def reject_replacement_request(
    request_id: uuid.UUID,
    payload: DeviceReplacementReviewRequest,
    current_user: Annotated[
        User, Depends(require_permission("devices.replacement_review", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[DeviceReplacementResponse]:
    """Reject a pending device replacement request with review note."""
    rejected_dto = await DeviceTrustService.reject_device_replacement(
        db=db,
        request_id=request_id,
        reviewer_user=current_user,
        payload=payload,
    )
    return StandardResponse(
        data=rejected_dto,
        meta={"message": "Device replacement request rejected."},
    )


@router.post(
    "/{device_id}/suspend",
    response_model=StandardResponse[TrustedDeviceResponse],
    status_code=status.HTTP_200_OK,
    summary="Suspend a registered student device",
)
async def suspend_device(
    device_id: uuid.UUID,
    payload: DeviceStatusUpdateRequest,
    current_user: Annotated[
        User, Depends(require_permission("devices.suspend", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[TrustedDeviceResponse]:
    """Administratively suspend a registered student device."""
    device_dto = await DeviceTrustService.suspend_device(
        db=db,
        device_id=device_id,
        actor_user=current_user,
        payload=payload,
    )
    return StandardResponse(
        data=device_dto,
        meta={"message": "Device suspended successfully."},
    )


@router.post(
    "/{device_id}/revoke",
    response_model=StandardResponse[TrustedDeviceResponse],
    status_code=status.HTTP_200_OK,
    summary="Revoke or mark a student device compromised",
)
async def revoke_device(
    device_id: uuid.UUID,
    payload: DeviceStatusUpdateRequest,
    current_user: Annotated[User, Depends(require_permission("devices.revoke", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[TrustedDeviceResponse]:
    """Administratively revoke or mark a student device compromised."""
    device_dto = await DeviceTrustService.revoke_device(
        db=db,
        device_id=device_id,
        actor_user=current_user,
        payload=payload,
    )
    return StandardResponse(
        data=device_dto,
        meta={"message": "Device revoked successfully."},
    )


@router.get(
    "/student/{student_id}",
    response_model=StandardResponse[list[TrustedDeviceResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get all historical and active devices for a student",
)
async def get_student_device_history(
    student_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("devices.read", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[list[TrustedDeviceResponse]]:
    """Retrieve complete device registry history for an individual student."""
    stmt = (
        select(TrustedDevice)
        .where(
            TrustedDevice.student_id == student_id,
            TrustedDevice.university_id == current_user.university_id,
        )
        .order_by(TrustedDevice.created_at.desc())
    )
    res = await db.execute(stmt)
    devices = res.scalars().all()

    dtos: list[TrustedDeviceResponse] = []
    for d in devices:
        dto = TrustedDeviceResponse.model_validate(d)
        dto.short_fingerprint = (
            f"{d.public_key_fingerprint[:6]}...{d.public_key_fingerprint[-6:]}".upper()
        )
        dtos.append(dto)

    return StandardResponse(
        data=dtos,
        meta={"total": len(dtos)},
    )


@router.get(
    "/events",
    response_model=StandardResponse[list[DeviceTrustEventResponse]],
    status_code=status.HTTP_200_OK,
    summary="List device security audit events",
)
async def list_device_events(
    current_user: Annotated[User, Depends(require_permission("devices.read", allow_scoped=True))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> StandardResponse[list[DeviceTrustEventResponse]]:
    """List immutable device security audit events for the university."""
    stmt = (
        select(DeviceTrustEvent)
        .where(DeviceTrustEvent.university_id == current_user.university_id)
        .order_by(DeviceTrustEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    records = res.scalars().all()

    items = [DeviceTrustEventResponse.model_validate(r) for r in records]
    return StandardResponse(
        data=items,
        meta={"total": len(items), "limit": limit, "offset": offset},
    )
