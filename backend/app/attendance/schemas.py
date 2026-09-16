"""Pydantic schemas and request/response contracts for Attendance domain."""

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.constants import (
    AttendanceStatus,
    EvidenceSourceMode,
    NetworkPresenceMode,
    PolicyScopeType,
    RecordStatus,
)
from backend.app.devices.schemas import DeviceProofSchema
from backend.app.security.schemas import NetworkProofSchema

# ==========================================
# Attendance Policy Schemas
# ==========================================


class AttendancePolicyCreateRequest(BaseModel):
    """Request payload to create an attendance policy."""

    name: str = Field(..., min_length=2, max_length=150)
    scope_type: PolicyScopeType = Field(default=PolicyScopeType.UNIVERSITY)
    scope_id: uuid.UUID | None = Field(default=None)
    academic_unit_id: uuid.UUID | None = Field(default=None)
    course_id: uuid.UUID | None = Field(default=None)
    min_attendance_percentage: float = Field(default=75.0, ge=0.0, le=100.0)
    late_threshold_minutes: int = Field(default=10, ge=0, le=120)
    lecturer_correction_window_hours: int = Field(default=24, ge=1, le=720)
    required_checkpoint_count: int = Field(default=3, ge=1, le=3)
    checkpoint_duration_seconds: int = Field(default=300, ge=60, le=3600)
    token_rotation_seconds: int = Field(default=30, ge=10, le=120)
    checkpoint_weights: dict[str, float] = Field(
        default_factory=lambda: {"START": 1.0, "MIDDLE": 1.0, "END": 1.0}
    )
    status_mapping: dict[str, str] = Field(
        default_factory=lambda: {
            "111": "PRESENT",
            "110": "PRESENT",
            "101": "PRESENT",
            "011": "LATE",
            "100": "LATE",
            "010": "LATE",
            "001": "ABSENT",
            "000": "ABSENT",
        }
    )
    effective_from: datetime.date | None = Field(default=None)
    effective_to: datetime.date | None = Field(default=None)
    network_presence_mode: NetworkPresenceMode = Field(default=NetworkPresenceMode.DISABLED)
    lecturer_network_presence_mode: NetworkPresenceMode = Field(
        default=NetworkPresenceMode.DISABLED
    )
    allow_university_wide_zones: bool = Field(default=True)


class AttendancePolicyUpdateRequest(BaseModel):
    """Request payload to update an attendance policy."""

    name: str | None = Field(default=None, min_length=2, max_length=150)
    min_attendance_percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    late_threshold_minutes: int | None = Field(default=None, ge=0, le=120)
    lecturer_correction_window_hours: int | None = Field(default=None, ge=1, le=720)
    required_checkpoint_count: int | None = Field(default=None, ge=1, le=3)
    checkpoint_duration_seconds: int | None = Field(default=None, ge=60, le=3600)
    token_rotation_seconds: int | None = Field(default=None, ge=10, le=120)
    checkpoint_weights: dict[str, float] | None = Field(default=None)
    status_mapping: dict[str, str] | None = Field(default=None)
    status: RecordStatus | None = Field(default=None)
    effective_from: datetime.date | None = Field(default=None)
    effective_to: datetime.date | None = Field(default=None)
    network_presence_mode: NetworkPresenceMode | None = Field(default=None)
    lecturer_network_presence_mode: NetworkPresenceMode | None = Field(default=None)
    allow_university_wide_zones: bool | None = Field(default=None)


class AttendancePolicyResponse(BaseModel):
    """Public representation of an attendance policy."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    academic_unit_id: uuid.UUID | None = None
    course_id: uuid.UUID | None = None
    name: str
    scope_type: str
    scope_id: uuid.UUID | None = None
    min_attendance_percentage: float
    late_threshold_minutes: int
    lecturer_correction_window_hours: int
    required_checkpoint_count: int
    checkpoint_duration_seconds: int
    token_rotation_seconds: int
    checkpoint_weights: dict[str, Any]
    status_mapping: dict[str, Any]
    status: str
    effective_from: datetime.date | None = None
    effective_to: datetime.date | None = None
    network_presence_mode: str = "DISABLED"
    lecturer_network_presence_mode: str = "DISABLED"
    allow_university_wide_zones: bool = True
    created_at: datetime.datetime
    updated_at: datetime.datetime


# ==========================================
# Attendance Checkpoint Schemas
# ==========================================


class CheckpointOpenRequest(BaseModel):
    """Request payload to open an attendance checkpoint."""

    window_duration_seconds: int | None = Field(
        default=None, ge=60, le=3600, description="Optional window duration override in seconds."
    )


class AttendanceCheckpointResponse(BaseModel):
    """Public representation of an attendance checkpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attendance_session_id: uuid.UUID
    checkpoint_type: str
    sequence_no: int
    status: str
    window_duration_seconds: int
    opened_at_utc: datetime.datetime | None = None
    closed_at_utc: datetime.datetime | None = None
    opened_by_user_id: uuid.UUID | None = None
    closed_by_user_id: uuid.UUID | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


# ==========================================
# Attendance Session Schemas
# ==========================================


class AttendanceSessionCreateRequest(BaseModel):
    """Request payload to initialize an attendance session for a class meeting."""

    class_occurrence_id: uuid.UUID
    attendance_policy_id: uuid.UUID | None = Field(
        default=None,
        description="Optional explicit policy override; if omitted, resolved hierarchically.",
    )
    activate_immediately: bool = Field(
        default=False,
        description="If true, transitions directly from SCHEDULED to ACTIVE and freezes roster.",
    )


class AttendanceSessionResponse(BaseModel):
    """Summary representation of an attendance session."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    class_occurrence_id: uuid.UUID
    attendance_policy_id: uuid.UUID | None = None
    policy_snapshot: dict[str, Any]
    status: str
    host_type: str
    opened_at_utc: datetime.datetime | None = None
    paused_at_utc: datetime.datetime | None = None
    resumed_at_utc: datetime.datetime | None = None
    closed_at_utc: datetime.datetime | None = None
    opened_by_user_id: uuid.UUID | None = None
    closed_by_user_id: uuid.UUID | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AttendanceSessionDetailResponse(AttendanceSessionResponse):
    """Detailed representation of an attendance session including checkpoints and counts."""

    checkpoints: list[AttendanceCheckpointResponse] = []
    total_enrolled: int = 0
    total_present: int = 0
    total_late: int = 0
    total_absent: int = 0
    total_excused: int = 0
    total_leave: int = 0
    total_pending: int = 0


# ==========================================
# Attendance Evidence & Checkpoint Credit Schemas
# ==========================================


class ManualCheckpointCreditRequest(BaseModel):
    """Request payload for authorized lecturer/staff manual checkpoint credit."""

    student_id: uuid.UUID
    reason: str = Field(..., min_length=3, max_length=500, description="Mandatory reason.")
    source_mode: EvidenceSourceMode = Field(default=EvidenceSourceMode.MANUAL)


class CheckpointCreditResponse(BaseModel):
    """Confirmation response for a granted checkpoint credit."""

    checkpoint_id: uuid.UUID
    student_id: uuid.UUID
    checkpoint_type: str
    verified: bool
    source_mode: str
    server_received_at_utc: datetime.datetime


# ==========================================
# Dynamic QR Schemas (Milestone 10)
# ==========================================


class QrTokenResponse(BaseModel):
    """Response payload for lecturer visual QR token display."""

    token: str
    checkpoint_id: uuid.UUID
    checkpoint_type: str
    issued_at: datetime.datetime
    expires_at: datetime.datetime
    rotation_seconds: int
    server_time: datetime.datetime
    refresh_after_seconds: int


class QrCheckInRequest(BaseModel):
    """Request payload for student self-service QR check-in."""

    token: str = Field(..., min_length=10, description="Scanned dynamic presence QR token.")
    device_proof: DeviceProofSchema | None = Field(
        default=None,
        description="Cryptographic proof of possession from primary trusted device.",
    )
    network_proof: NetworkProofSchema | None = Field(
        default=None,
        description="Cryptographic proof of campus network presence.",
    )


class QrCheckInResponse(BaseModel):
    """Confirmation response for a verified dynamic QR check-in."""

    accepted: bool
    checkpoint_type: str
    already_credited: bool
    verified_at: datetime.datetime
    attendance_record_id: uuid.UUID


# ==========================================
# Bluetooth BLE & Unified Presence Schemas (Milestone 11)
# ==========================================


class BleAdvertisementResponse(BaseModel):
    """Response payload for lecturer mobile BLE classroom presence broadcast."""

    service_uuid: str = Field(..., description="Configured 128-bit attendance BLE service UUID.")
    payload_base64: str = Field(..., description="Base64-encoded 17-byte compact presence payload.")
    payload_hex: str = Field(..., description="Hex-encoded 17-byte compact presence payload.")
    protocol_version: int = Field(default=1)
    rotation_seconds: int = Field(..., description="Ephemeral rotation interval in seconds.")
    issued_at: datetime.datetime
    expires_at: datetime.datetime
    checkpoint_id: uuid.UUID
    checkpoint_type: str
    server_time: datetime.datetime
    refresh_after_seconds: int


class BleObservationSchema(BaseModel):
    """Client-observed Bluetooth Low Energy telemetry payload."""

    payload: str = Field(
        ..., min_length=1, description="Observed BLE payload in base64 or hex format."
    )
    rssi: int | None = Field(
        default=None, description="Observed Received Signal Strength Indication in dBm."
    )
    observed_at_client: datetime.datetime | None = Field(
        default=None,
        description="Client device timestamp (telemetry only; non-authoritative).",
    )
    platform: str | None = Field(
        default=None, max_length=50, description="Scanning platform (e.g., android, ios)."
    )


class PresenceCheckInRequest(BaseModel):
    """Unified presence check-in request supporting multi-factor evidence (QR + BLE)."""

    qr_token: str | None = Field(
        default=None, description="Dynamic classroom QR token if captured."
    )
    ble_observation: BleObservationSchema | None = Field(
        default=None,
        description="Classroom BLE observation telemetry if captured.",
    )
    device_proof: DeviceProofSchema | None = Field(
        default=None,
        description="Cryptographic proof of possession from primary trusted device.",
    )
    network_proof: NetworkProofSchema | None = Field(
        default=None,
        description="Cryptographic proof of campus network presence.",
    )


class PresenceCheckInResponse(BaseModel):
    """Unified response for multi-factor presence evaluation and checkpoint credit."""

    accepted: bool
    checkpoint_type: str
    already_credited: bool
    verified_at: datetime.datetime
    attendance_record_id: uuid.UUID
    verified_factors: list[str] = Field(
        default_factory=list,
        description="Evidence modalities verified (e.g. ONLINE_DYNAMIC_QR, BLUETOOTH_BLE).",
    )
    presence_mode: str = Field(
        default="QR_ONLY",
        description="Effective policy presence requirement mode (e.g. QR_ONLY, QR_AND_BLE).",
    )


# ==========================================
# Attendance Record Schemas
# ==========================================


class AttendanceRecordResponse(BaseModel):
    """Public representation of a student attendance record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attendance_session_id: uuid.UUID
    student_id: uuid.UUID
    status: str
    start_credited: bool
    middle_credited: bool
    end_credited: bool
    checkpoints_verified: int
    attendance_credit: float
    is_manual: bool
    manual_reason: str | None = None
    calculation_snapshot: dict[str, Any] | None = None
    finalized_at_utc: datetime.datetime | None = None
    version_no: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AttendanceRecordOverrideRequest(BaseModel):
    """Request payload for manual status override (INV-08)."""

    status: AttendanceStatus = Field(
        ...,
        description="Target status (PRESENT, LATE, ABSENT, EXCUSED, LEAVE).",
    )
    reason: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Mandatory justification recorded in immutable audit revision ledger.",
    )
    attendance_credit: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional custom credit override; defaults according to policy status.",
    )


class StudentAttendanceSelfResponse(BaseModel):
    """Student personal attendance history response."""

    model_config = ConfigDict(from_attributes=True)

    record_id: uuid.UUID
    session_id: uuid.UUID
    class_occurrence_id: uuid.UUID
    course_code: str
    course_name: str
    occurrence_date: datetime.date
    scheduled_start_utc: datetime.datetime
    scheduled_end_utc: datetime.datetime
    status: str
    attendance_credit: float
    checkpoints_verified: int
    start_credited: bool
    middle_credited: bool
    end_credited: bool
    is_manual: bool
    finalized_at_utc: datetime.datetime | None = None


# ==========================================
# Attendance Revision / Audit Schemas
# ==========================================


class AttendanceRevisionResponse(BaseModel):
    """Public representation of an append-only audit revision entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attendance_session_id: uuid.UUID
    attendance_record_id: uuid.UUID | None = None
    actor_user_id: uuid.UUID
    event_type: str
    previous_status: str | None = None
    new_status: str | None = None
    previous_credit: float | None = None
    new_credit: float | None = None
    reason: str | None = None
    metadata_json: dict[str, Any] | None = None
    occurred_at_utc: datetime.datetime
    created_at: datetime.datetime
