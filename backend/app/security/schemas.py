"""Pydantic schemas for Milestone 14 Campus Presence, Anti-Cheat, and Radio Analysis."""

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.constants import (
    NetworkZoneStatus,
    NetworkZoneType,
)

# =============================================================================
# 1. Campus Network Zone Schemas
# =============================================================================


class CampusNetworkZoneCreateRequest(BaseModel):
    """Admin payload to create a new campus network zone."""

    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    network_cidr: str = Field(..., min_length=7, max_length=64)
    ip_version: int = Field(default=4, ge=4, le=6)
    building_id: uuid.UUID | None = None
    zone_type: str = Field(default=NetworkZoneType.CAMPUS_TRUSTED.value)
    status: str = Field(default=NetworkZoneStatus.ACTIVE.value)
    allow_student_presence: bool = True
    allow_lecturer_operations: bool = True
    priority: int = Field(default=100, ge=1, le=1000)


class CampusNetworkZoneUpdateRequest(BaseModel):
    """Admin payload to update an existing campus network zone."""

    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    network_cidr: str | None = Field(default=None, min_length=7, max_length=64)
    ip_version: int | None = Field(default=None, ge=4, le=6)
    building_id: uuid.UUID | None = None
    zone_type: str | None = None
    status: str | None = None
    allow_student_presence: bool | None = None
    allow_lecturer_operations: bool | None = None
    priority: int | None = Field(default=None, ge=1, le=1000)


class CampusNetworkZoneResponse(BaseModel):
    """Serialized campus network zone response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    building_id: uuid.UUID | None
    code: str
    name: str
    description: str | None
    network_cidr: str
    ip_version: int
    zone_type: str
    status: str
    allow_student_presence: bool
    allow_lecturer_operations: bool
    priority: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


# =============================================================================
# 2. Campus Network Challenge & Proof Schemas
# =============================================================================


class NetworkChallengeRequest(BaseModel):
    """Student request to obtain a short-lived network presence challenge.

    Invariants Enforced:
    - Student ID is NOT accepted from the client; it is derived from auth credentials.
    - Checkpoint ID anchors the challenge to the active session.
    """

    checkpoint_id: uuid.UUID


class NetworkChallengeResponse(BaseModel):
    """Short-lived challenge returned to student upon verified campus network resolution."""

    challenge_id: uuid.UUID
    network_zone_id: uuid.UUID
    network_zone_name: str
    network_zone_code: str
    nonce: str
    status: str
    issued_at: datetime.datetime
    expires_at: datetime.datetime
    ttl_seconds: int


class NetworkProofSchema(BaseModel):
    """Cryptographic proof of network presence signed by student's registered M13 device."""

    version: str = "NETWORK_PRESENCE_V1"
    challenge_id: uuid.UUID
    trusted_device_id: uuid.UUID
    proof_id: uuid.UUID
    signature: str


# =============================================================================
# 3. Anti-Cheat Risk Signal Schemas
# =============================================================================


class AttendanceRiskSignalResponse(BaseModel):
    """Detailed anti-cheat risk signal representation for human audit and review."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    signal_type: str
    severity: str
    risk_points: int | None
    subject_type: str
    subject_user_id: uuid.UUID | None
    trusted_device_id: uuid.UUID | None
    attendance_session_id: uuid.UUID | None
    class_occurrence_id: uuid.UUID | None
    course_offering_id: uuid.UUID | None
    context: dict[str, Any] | None
    rule_version: str
    risk_key: str
    detected_at: datetime.datetime
    status: str
    reviewed_at: datetime.datetime | None
    reviewed_by_user_id: uuid.UUID | None
    review_note: str | None
    resolved_at: datetime.datetime | None
    created_at: datetime.datetime


class RiskSignalReviewRequest(BaseModel):
    """Staff review action payload for acknowledging, resolving, or dismissing a signal."""

    review_note: str = Field(..., min_length=3, max_length=1000)


# =============================================================================
# 4. Radio Analysis Schemas
# =============================================================================


class RadioAnalysisSummary(BaseModel):
    """Aggregated classroom BLE radio environment metrics."""

    observation_count: int
    median_rssi: float | None
    p10_rssi: float | None
    p25_rssi: float | None
    p75_rssi: float | None
    p90_rssi: float | None
    min_rssi: int | None
    max_rssi: int | None
    building_id: uuid.UUID | None = None
    room_id: uuid.UUID | None = None
    attendance_session_id: uuid.UUID | None = None
    time_window_start: datetime.datetime | None = None
    time_window_end: datetime.datetime | None = None
