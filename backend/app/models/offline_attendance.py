"""Declarative SQLAlchemy models for Milestone 12 Offline Attendance & Sync."""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.common.types import utc_now
from backend.app.core.constants import (
    OfflineClaimStatus,
    OfflineConflictResolution,
    OfflineHostSessionStatus,
    OfflinePermitStatus,
    SyncEntryStatus,
)
from backend.app.models.base import Base, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.attendance_evidence import AttendanceEvidence
    from backend.app.models.attendance_session import AttendanceSession
    from backend.app.models.class_occurrence import ClassOccurrence
    from backend.app.models.student import Student
    from backend.app.models.trusted_device import TrustedDevice
    from backend.app.models.university import University
    from backend.app.models.user import User


class OfflineAttendancePermit(Base, UUIDv7PrimaryKeyMixin):
    """Pre-issued, cryptographically signed permit authorizing offline attendance hosting."""

    __tablename__ = "offline_attendance_permits"
    __table_args__ = (
        Index("ix_offline_permits_session_id", "attendance_session_id"),
        Index("ix_offline_permits_occurrence_id", "class_occurrence_id"),
        Index("ix_offline_permits_lecturer_id", "lecturer_user_id"),
        Index("ix_offline_permits_status", "status"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attendance_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    class_occurrence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("class_occurrences.id", ondelete="RESTRICT"),
        nullable=False,
    )
    lecturer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    temporary_host_public_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    authority_epoch: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    roster_snapshot_digest: Mapped[str] = mapped_column(
        String(64),
        default="",
        nullable=False,
    )
    policy_snapshot_digest: Mapped[str] = mapped_column(
        String(64),
        default="",
        nullable=False,
    )
    valid_from_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    valid_until_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=OfflinePermitStatus.ISSUED.value,
        nullable=False,
    )
    signed_permit_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    university: Mapped[University] = relationship("University")
    session: Mapped[AttendanceSession] = relationship("AttendanceSession")
    occurrence: Mapped[ClassOccurrence] = relationship("ClassOccurrence")
    lecturer_user: Mapped[User] = relationship("User", foreign_keys=[lecturer_user_id])
    host_sessions: Mapped[list[OfflineHostSession]] = relationship(
        "OfflineHostSession",
        back_populates="permit",
        cascade="all, delete-orphan",
    )
    claims: Mapped[list[OfflineAttendanceClaim]] = relationship(
        "OfflineAttendanceClaim",
        back_populates="permit",
    )


class OfflineHostSession(Base, UUIDv7PrimaryKeyMixin):
    """Operational offline session executed on lecturer device bound to a permit."""

    __tablename__ = "offline_host_sessions"
    __table_args__ = (
        Index("ix_offline_host_sessions_permit_id", "offline_permit_id"),
        Index("ix_offline_host_sessions_status", "status"),
    )

    offline_permit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offline_attendance_permits.id", ondelete="CASCADE"),
        nullable=False,
    )
    host_device_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    clock_anchor_server_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    clock_anchor_uptime_ms: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    started_at_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ended_at_utc: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    final_event_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=OfflineHostSessionStatus.ACTIVE.value,
        nullable=False,
    )
    synced_at_utc: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    permit: Mapped[OfflineAttendancePermit] = relationship(
        "OfflineAttendancePermit",
        back_populates="host_sessions",
    )
    events: Mapped[list[OfflineHostEvent]] = relationship(
        "OfflineHostEvent",
        back_populates="host_session",
        cascade="all, delete-orphan",
        order_by="OfflineHostEvent.sequence_number",
    )
    claims: Mapped[list[OfflineAttendanceClaim]] = relationship(
        "OfflineAttendanceClaim",
        back_populates="host_session",
    )


class OfflineHostEvent(Base, UUIDv7PrimaryKeyMixin):
    """Tamper-evident append-only event recorded in the host session hash chain."""

    __tablename__ = "offline_host_events"
    __table_args__ = (
        UniqueConstraint(
            "offline_host_session_id",
            "sequence_number",
            name="uq_offline_host_events_session_seq",
        ),
        Index("ix_offline_host_events_session_id", "offline_host_session_id"),
    )

    offline_host_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offline_host_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    prev_event_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    event_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    signature: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    occurred_at_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    host_session: Mapped[OfflineHostSession] = relationship(
        "OfflineHostSession",
        back_populates="events",
    )


class OfflineAttendanceClaim(Base, UUIDv7PrimaryKeyMixin):
    """Student attendance evidence captured offline and synced to the backend."""

    __tablename__ = "offline_attendance_claims"
    __table_args__ = (
        UniqueConstraint(
            "offline_permit_id",
            "student_id",
            "checkpoint_type",
            name="uq_offline_claims_permit_student_cpt",
        ),
        Index("ix_offline_claims_permit_id", "offline_permit_id"),
        Index("ix_offline_claims_student_id", "student_id"),
        Index("ix_offline_claims_device_id", "trusted_device_id"),
        Index("ix_offline_claims_status", "status"),
    )

    offline_permit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offline_attendance_permits.id", ondelete="RESTRICT"),
        nullable=False,
    )
    offline_host_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offline_host_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
    )
    submitted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    checkpoint_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    rotation_slot: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    qr_challenge_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    ble_evidence_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default=OfflineClaimStatus.PENDING_HOST_EVENTS.value,
        nullable=False,
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    attendance_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_evidence.id", ondelete="SET NULL"),
        nullable=True,
    )
    trusted_device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trusted_devices.id", ondelete="SET NULL"),
        nullable=True,
    )
    device_proof_signature: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    client_monotonic_offset_ms: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    client_captured_at_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    server_synced_at_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    permit: Mapped[OfflineAttendancePermit] = relationship(
        "OfflineAttendancePermit",
        back_populates="claims",
    )
    host_session: Mapped[OfflineHostSession | None] = relationship(
        "OfflineHostSession",
        back_populates="claims",
    )
    student: Mapped[Student] = relationship("Student")
    submitted_by_user: Mapped[User] = relationship("User", foreign_keys=[submitted_by_user_id])
    evidence: Mapped[AttendanceEvidence | None] = relationship("AttendanceEvidence")
    trusted_device: Mapped[TrustedDevice | None] = relationship("TrustedDevice")


class SyncInboxEntry(Base, UUIDv7PrimaryKeyMixin):
    """Idempotent sync deduplication inbox tracking incoming batch uploads."""

    __tablename__ = "sync_inbox_entries"
    __table_args__ = (
        UniqueConstraint(
            "client_batch_id",
            "idempotency_key",
            name="uq_sync_inbox_batch_idempotency",
        ),
        Index("ix_sync_inbox_actor_id", "actor_user_id"),
        Index("ix_sync_inbox_status", "status"),
    )

    client_batch_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    batch_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    payload_digest: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=SyncEntryStatus.PROCESSED.value,
        nullable=False,
    )
    processed_at_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class OfflineSyncConflict(Base, UUIDv7PrimaryKeyMixin):
    """Audit log and review queue for disputed or unreconciled offline attendance events."""

    __tablename__ = "offline_sync_conflicts"
    __table_args__ = (
        Index("ix_offline_conflicts_session_id", "attendance_session_id"),
        Index("ix_offline_conflicts_permit_id", "offline_permit_id"),
        Index("ix_offline_conflicts_status", "resolution_status"),
    )

    attendance_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    offline_permit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offline_attendance_permits.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="SET NULL"),
        nullable=True,
    )
    conflict_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    resolution_status: Mapped[str] = mapped_column(
        String(30),
        default=OfflineConflictResolution.UNRESOLVED.value,
        nullable=False,
    )
    conflict_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at_utc: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolution_notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
