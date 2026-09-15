"""Pydantic schemas for Milestone 12 Offline Attendance & Reconciliation."""

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OfflineVerificationKeyResponse(BaseModel):
    """Public verification key schema for offline clients."""

    model_config = ConfigDict(from_attributes=True)

    algorithm: str = "EdDSA"
    curve: str = "Ed25519"
    kid: str
    public_key_pem: str


class OfflinePermitRequest(BaseModel):
    """Request payload for an authorized lecturer to obtain an offline permit."""

    attendance_session_id: uuid.UUID
    temporary_host_public_key: str = Field(
        ...,
        description="Lecturer's ephemeral Ed25519 public key in PEM or raw hex format.",
    )
    validity_hours: int = Field(default=12, ge=1, le=48)


class OfflinePermitResponse(BaseModel):
    """Signed offline permit returned to lecturer device."""

    model_config = ConfigDict(from_attributes=True)

    permit_id: uuid.UUID
    attendance_session_id: uuid.UUID
    class_occurrence_id: uuid.UUID
    lecturer_user_id: uuid.UUID
    temporary_host_public_key: str
    authority_epoch: int
    roster_snapshot_digest: str
    policy_snapshot_digest: str
    valid_from_utc: datetime.datetime
    valid_until_utc: datetime.datetime
    status: str
    signed_permit_token: str
    server_time_utc: datetime.datetime


class OfflineHostEventPayload(BaseModel):
    """Single event item in the host hash-chain upload."""

    sequence_number: int
    event_type: str
    prev_event_hash: str
    event_hash: str
    payload: dict[str, Any]
    signature: str
    occurred_at_utc: str


class OfflineHostSyncRequest(BaseModel):
    """Lecturer upload of offline host session event chain."""

    client_batch_id: str = Field(..., max_length=100)
    idempotency_key: str = Field(..., max_length=100)
    permit_id: uuid.UUID
    host_session_id: uuid.UUID
    host_device_id: str = Field(..., max_length=128)
    clock_anchor_server_utc: datetime.datetime
    clock_anchor_uptime_ms: int
    started_at_utc: datetime.datetime
    ended_at_utc: datetime.datetime | None = None
    final_event_hash: str | None = None
    events: list[OfflineHostEventPayload] = Field(default_factory=list)


class OfflineHostSyncResponse(BaseModel):
    """Reconciliation result returned to lecturer after host events sync."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    host_session_id: uuid.UUID
    events_ingested: int
    claims_reconciled: int
    conflicts_detected: int


class OfflineStudentClaimItem(BaseModel):
    """Individual offline attendance claim submitted by student."""

    claim_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    permit_id: uuid.UUID
    host_session_id: uuid.UUID | None = None
    checkpoint_type: str
    rotation_slot: int
    qr_challenge_token: str
    ble_evidence: dict[str, Any] | None = None
    client_monotonic_offset_ms: int | None = None
    client_captured_at_utc: datetime.datetime
    trusted_device_id: uuid.UUID | None = Field(
        default=None,
        description="ID of student's trusted device that captured the claim.",
    )
    device_proof_signature: str | None = Field(
        default=None,
        description="Cryptographic Ed25519 signature over canonical offline claim payload.",
    )


class OfflineStudentSyncRequest(BaseModel):
    """Student upload of locally queued offline claims."""

    client_batch_id: str = Field(..., max_length=100)
    idempotency_key: str = Field(..., max_length=100)
    claims: list[OfflineStudentClaimItem] = Field(default_factory=list)


class OfflineStudentClaimSyncResult(BaseModel):
    """Outcome for an individual student offline attendance claim."""

    claim_id: uuid.UUID
    checkpoint_type: str
    status: str
    rejection_reason: str | None = None
    credited: bool = False


class OfflineStudentSyncResponse(BaseModel):
    """Batch result returned to student mobile app."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    claims_processed: int
    results: list[OfflineStudentClaimSyncResult]


class OfflineConflictResponse(BaseModel):
    """Conflict details for administrative inspection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attendance_session_id: uuid.UUID
    offline_permit_id: uuid.UUID
    student_id: uuid.UUID | None
    conflict_type: str
    resolution_status: str
    conflict_details: dict[str, Any] | None
    created_at: datetime.datetime


class OfflineConflictResolveRequest(BaseModel):
    """Admin payload to resolve an offline synchronization conflict."""

    resolution_status: str = Field(
        ...,
        description="Must be RESOLVED_MANUAL or DISMISSED",
    )
    resolution_notes: str = Field(..., max_length=500)
    credit_checkpoint: bool = Field(
        default=False,
        description="If True, credit the student's checkpoint record as part of resolution.",
    )
    checkpoint_type: str | None = Field(
        default=None,
        description="START, MIDDLE, or END if credit_checkpoint is True.",
    )
