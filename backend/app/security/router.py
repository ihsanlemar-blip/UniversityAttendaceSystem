"""API Router for Milestone 14: Campus Network Presence, Radio Diagnostics, and Anti-Cheat."""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.schemas import StandardResponse
from backend.app.core.database import get_db_session
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_permission
from backend.app.security.network_service import CampusNetworkService
from backend.app.security.radio_service import RadioAnalysisService
from backend.app.security.resolver import ClientNetworkResolver
from backend.app.security.risk_service import AntiCheatService
from backend.app.security.schemas import (
    AttendanceRiskSignalResponse,
    CampusNetworkZoneCreateRequest,
    CampusNetworkZoneResponse,
    CampusNetworkZoneUpdateRequest,
    RadioAnalysisSummary,
    RiskSignalReviewRequest,
)

router = APIRouter(prefix="/security", tags=["Campus Network & Anti-Cheat Security"])


# =============================================================================
# 1. Campus Network Zones Administration
# =============================================================================


@router.get(
    "/network-zones",
    response_model=StandardResponse[list[CampusNetworkZoneResponse]],
    summary="List campus network zones",
)
async def list_campus_network_zones(
    current_user: Annotated[
        User, Depends(require_permission("security.network_zones.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    building_id: Annotated[uuid.UUID | None, Query()] = None,
) -> StandardResponse[list[CampusNetworkZoneResponse]]:
    """List configured campus network CIDR zones for the authenticated university."""
    zones = await CampusNetworkService.list_network_zones(
        db=db,
        university_id=current_user.university_id,
        status=status_filter,
        building_id=building_id,
    )
    return StandardResponse(
        data=zones,
        meta={"message": f"Retrieved {len(zones)} campus network zones."},
    )


@router.post(
    "/network-zones",
    response_model=StandardResponse[CampusNetworkZoneResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create campus network zone",
)
async def create_campus_network_zone(
    payload: CampusNetworkZoneCreateRequest,
    current_user: Annotated[
        User, Depends(require_permission("security.network_zones.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CampusNetworkZoneResponse]:
    """Create a new campus network CIDR zone bound to university and optional building."""
    zone = await CampusNetworkService.create_network_zone(
        db=db,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=zone,
        meta={"message": "Campus network zone created successfully."},
    )


@router.patch(
    "/network-zones/{zone_id}",
    response_model=StandardResponse[CampusNetworkZoneResponse],
    summary="Update campus network zone",
)
async def update_campus_network_zone(
    zone_id: uuid.UUID,
    payload: CampusNetworkZoneUpdateRequest,
    current_user: Annotated[
        User, Depends(require_permission("security.network_zones.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CampusNetworkZoneResponse]:
    """Update configurable attributes of an existing campus network zone."""
    zone = await CampusNetworkService.update_network_zone(
        db=db,
        zone_id=zone_id,
        university_id=current_user.university_id,
        payload=payload,
    )
    return StandardResponse(
        data=zone,
        meta={"message": "Campus network zone updated successfully."},
    )


@router.get(
    "/network-zones/{zone_id}",
    response_model=StandardResponse[CampusNetworkZoneResponse],
    summary="Get campus network zone details",
)
async def get_campus_network_zone(
    zone_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("security.network_zones.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CampusNetworkZoneResponse]:
    """Get details of a single campus network zone."""
    zone = await CampusNetworkService.get_network_zone(
        db=db,
        zone_id=zone_id,
        university_id=current_user.university_id,
    )
    return StandardResponse(
        data=zone,
        meta={"message": "Campus network zone retrieved successfully."},
    )


@router.post(
    "/network-zones/{zone_id}/disable",
    response_model=StandardResponse[CampusNetworkZoneResponse],
    summary="Disable campus network zone",
)
async def disable_campus_network_zone(
    zone_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("security.network_zones.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CampusNetworkZoneResponse]:
    """Disable a campus network zone so it no longer satisfies attendance presence."""
    zone = await CampusNetworkService.disable_network_zone(
        db=db,
        zone_id=zone_id,
        university_id=current_user.university_id,
    )
    return StandardResponse(
        data=zone,
        meta={"message": "Campus network zone disabled successfully."},
    )


@router.delete(
    "/network-zones/{zone_id}",
    response_model=StandardResponse[CampusNetworkZoneResponse],
    summary="Delete/disable campus network zone",
)
async def delete_campus_network_zone(
    zone_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("security.network_zones.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[CampusNetworkZoneResponse]:
    """Deactivate/disable a campus network zone."""
    zone = await CampusNetworkService.disable_network_zone(
        db=db,
        zone_id=zone_id,
        university_id=current_user.university_id,
    )
    return StandardResponse(
        data=zone,
        meta={"message": "Campus network zone disabled successfully."},
    )


@router.get(
    "/network-zones/diagnostics",
    response_model=StandardResponse[dict[str, Any]],
    summary="Inspect current request network resolution diagnostic",
)
async def get_network_diagnostics(
    request: Request,
    current_user: Annotated[
        User, Depends(require_permission("security.network_zones.manage", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[dict[str, Any]]:
    """Administrative diagnostic inspecting observed source IP, proxy parsing, and matched zone."""
    effective_ip, is_forwarded, spoof_detected = ClientNetworkResolver.extract_effective_client_ip(
        request
    )
    matched_zone = await ClientNetworkResolver.match_campus_network_zone(
        db=db,
        university_id=current_user.university_id,
        client_ip=effective_ip,
        allow_vpn=True,
    )
    diagnostic_data = {
        "observed_ip": effective_ip,
        "is_forwarded": is_forwarded,
        "spoof_detected": spoof_detected,
        "matched_zone_id": str(matched_zone.id) if matched_zone else None,
        "matched_zone_name": matched_zone.name if matched_zone else None,
        "matched_zone_code": matched_zone.code if matched_zone else None,
        "trusted": matched_zone is not None,
    }
    return StandardResponse(
        data=diagnostic_data,
        meta={"message": "Network resolution diagnostic completed."},
    )


# =============================================================================
# 2. Anti-Cheat Risk Signals Review
# =============================================================================


@router.get(
    "/risk-signals",
    response_model=StandardResponse[list[AttendanceRiskSignalResponse]],
    summary="List anti-cheat risk signals",
)
async def list_risk_signals(
    current_user: Annotated[
        User, Depends(require_permission("security.risk_signals.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    severity: Annotated[str | None, Query()] = None,
    signal_type: Annotated[str | None, Query()] = None,
    subject_user_id: Annotated[uuid.UUID | None, Query()] = None,
    session_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> StandardResponse[list[AttendanceRiskSignalResponse]]:
    """List anti-cheat risk signals for human administrative review."""
    signals = await AntiCheatService.list_risk_signals(
        db=db,
        university_id=current_user.university_id,
        status=status_filter,
        severity=severity,
        signal_type=signal_type,
        subject_user_id=subject_user_id,
        session_id=session_id,
        limit=limit,
        offset=offset,
    )
    return StandardResponse(
        data=signals,
        meta={"message": f"Retrieved {len(signals)} risk signals."},
    )


@router.get(
    "/risk-signals/{signal_id}",
    response_model=StandardResponse[AttendanceRiskSignalResponse],
    summary="Get anti-cheat risk signal detail",
)
async def get_risk_signal_detail(
    signal_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("security.risk_signals.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceRiskSignalResponse]:
    """Retrieve full detail, context, and review history for a specific risk signal."""
    signal = await AntiCheatService.get_risk_signal(
        db=db,
        signal_id=signal_id,
        university_id=current_user.university_id,
    )
    return StandardResponse(
        data=signal,
        meta={"message": "Risk signal retrieved successfully."},
    )


@router.post(
    "/risk-signals/{signal_id}/acknowledge",
    response_model=StandardResponse[AttendanceRiskSignalResponse],
    summary="Acknowledge anti-cheat risk signal",
)
async def acknowledge_risk_signal(
    signal_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_permission("security.risk_signals.review", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceRiskSignalResponse]:
    """Mark a risk signal as acknowledged by staff under investigation."""
    signal = await AntiCheatService.acknowledge_signal(
        db=db,
        signal_id=signal_id,
        university_id=current_user.university_id,
        reviewer_user_id=current_user.id,
    )
    return StandardResponse(
        data=signal,
        meta={"message": "Risk signal acknowledged."},
    )


@router.post(
    "/risk-signals/{signal_id}/resolve",
    response_model=StandardResponse[AttendanceRiskSignalResponse],
    summary="Resolve anti-cheat risk signal",
)
async def resolve_risk_signal(
    signal_id: uuid.UUID,
    payload: RiskSignalReviewRequest,
    current_user: Annotated[
        User, Depends(require_permission("security.risk_signals.review", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceRiskSignalResponse]:
    """Resolve a risk signal with mandatory explanation note."""
    signal = await AntiCheatService.resolve_signal(
        db=db,
        signal_id=signal_id,
        university_id=current_user.university_id,
        reviewer_user_id=current_user.id,
        review_note=payload.review_note,
    )
    return StandardResponse(
        data=signal,
        meta={"message": "Risk signal resolved successfully."},
    )


@router.post(
    "/risk-signals/{signal_id}/dismiss",
    response_model=StandardResponse[AttendanceRiskSignalResponse],
    summary="Dismiss false-positive risk signal",
)
async def dismiss_risk_signal(
    signal_id: uuid.UUID,
    payload: RiskSignalReviewRequest,
    current_user: Annotated[
        User, Depends(require_permission("security.risk_signals.review", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[AttendanceRiskSignalResponse]:
    """Dismiss a false-positive risk signal with mandatory explanation note."""
    signal = await AntiCheatService.dismiss_signal(
        db=db,
        signal_id=signal_id,
        university_id=current_user.university_id,
        reviewer_user_id=current_user.id,
        review_note=payload.review_note,
    )
    return StandardResponse(
        data=signal,
        meta={"message": "Risk signal dismissed successfully."},
    )


# =============================================================================
# 3. Radio Environment Analysis
# =============================================================================


@router.get(
    "/radio-analysis",
    response_model=StandardResponse[RadioAnalysisSummary],
    summary="Get aggregated classroom BLE radio diagnostics",
)
async def get_radio_analysis(
    current_user: Annotated[
        User, Depends(require_permission("security.radio_analysis.read", allow_scoped=True))
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    building_id: Annotated[uuid.UUID | None, Query()] = None,
    room_id: Annotated[uuid.UUID | None, Query()] = None,
    session_id: Annotated[uuid.UUID | None, Query()] = None,
    time_window_start: Annotated[datetime.datetime | None, Query()] = None,
    time_window_end: Annotated[datetime.datetime | None, Query()] = None,
) -> StandardResponse[RadioAnalysisSummary]:
    """Compute aggregated classroom BLE RSSI diagnostics (count, median, percentiles, min/max)."""
    summary = await RadioAnalysisService.analyze_radio_environment(
        db=db,
        university_id=current_user.university_id,
        building_id=building_id,
        room_id=room_id,
        session_id=session_id,
        time_window_start=time_window_start,
        time_window_end=time_window_end,
    )
    return StandardResponse(
        data=summary,
        meta={"message": "Radio environment analysis computed successfully."},
    )
