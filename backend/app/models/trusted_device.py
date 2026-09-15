"""Declarative SQLAlchemy models for Milestone 13 Student Device Registration & Trust."""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.common.types import utc_now
from backend.app.core.constants import (
    DeviceReplacementStatus,
    DeviceRole,
    DeviceStatus,
)
from backend.app.models.base import Base, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.student import Student
    from backend.app.models.university import University
    from backend.app.models.user import User


class TrustedDevice(Base, UUIDv7PrimaryKeyMixin):
    """Registered student primary mobile device bound via asymmetric cryptography."""

    __tablename__ = "trusted_devices"
    __table_args__ = (
        # Exactly ONE ACTIVE primary device per Student enforced at database level
        Index(
            "uq_trusted_devices_active_student",
            "student_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index("ix_trusted_devices_uni_user", "university_id", "user_id"),
        Index("ix_trusted_devices_uni_student", "university_id", "student_id"),
        Index("ix_trusted_devices_status", "status"),
        Index("ix_trusted_devices_fingerprint", "public_key_fingerprint", unique=True),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
    )
    device_role: Mapped[str] = mapped_column(
        String(20),
        default=DeviceRole.PRIMARY.value,
        nullable=False,
    )
    public_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    public_key_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    installation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    platform: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    device_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    app_version: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default=DeviceStatus.PENDING_REGISTRATION.value,
        nullable=False,
    )
    activated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    suspended_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    replaced_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    replaced_by_device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trusted_devices.id", ondelete="SET NULL"),
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

    # Relationships
    university: Mapped[University] = relationship("University")
    user: Mapped[User] = relationship("User", foreign_keys=[user_id])
    student: Mapped[Student] = relationship("Student")
    replaced_by: Mapped[TrustedDevice | None] = relationship(
        "TrustedDevice", remote_side="TrustedDevice.id"
    )


class DeviceRegistrationChallenge(Base, UUIDv7PrimaryKeyMixin):
    """Single-use cryptographic challenge for device registration proof of possession."""

    __tablename__ = "device_registration_challenges"
    __table_args__ = (
        Index(
            "ix_device_reg_challenges_user_active",
            "user_id",
            "purpose",
            "used_at",
            "expires_at",
        ),
        Index("ix_device_reg_challenges_fingerprint", "candidate_fingerprint"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
    )
    candidate_public_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    candidate_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    candidate_installation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    platform: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    device_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    app_version: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    purpose: Mapped[str] = mapped_column(
        String(30),
        default="DEVICE_REGISTRATION",
        nullable=False,
    )
    nonce: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    canonical_challenge: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    university: Mapped[University] = relationship("University")
    user: Mapped[User] = relationship("User")
    student: Mapped[Student] = relationship("Student")


class DeviceReplacementRequest(Base, UUIDv7PrimaryKeyMixin):
    """Student request to replace primary device, requiring administrative review."""

    __tablename__ = "device_replacement_requests"
    __table_args__ = (
        Index("ix_device_replacements_uni_status", "university_id", "status"),
        Index("ix_device_replacements_student_status", "student_id", "status"),
        Index("ix_device_replacements_requested_at", "requested_at"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    old_device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trusted_devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    candidate_public_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    candidate_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    candidate_installation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    candidate_platform: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    candidate_device_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    candidate_app_version: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default=DeviceReplacementStatus.PENDING.value,
        nullable=False,
    )
    requested_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    approved_device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trusted_devices.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    university: Mapped[University] = relationship("University")
    student: Mapped[Student] = relationship("Student")
    student_user: Mapped[User] = relationship("User", foreign_keys=[student_user_id])
    old_device: Mapped[TrustedDevice] = relationship("TrustedDevice", foreign_keys=[old_device_id])
    approved_device: Mapped[TrustedDevice | None] = relationship(
        "TrustedDevice", foreign_keys=[approved_device_id]
    )
    reviewed_by: Mapped[User | None] = relationship("User", foreign_keys=[reviewed_by_user_id])


class DeviceTrustEvent(Base, UUIDv7PrimaryKeyMixin):
    """Append-only audit ledger recording device trust and lifecycle events."""

    __tablename__ = "device_trust_events"
    __table_args__ = (
        Index("ix_device_trust_events_uni_user", "university_id", "target_user_id", "created_at"),
        Index("ix_device_trust_events_device_id", "device_id"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trusted_devices.id", ondelete="SET NULL"),
        nullable=True,
    )
    replacement_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device_replacement_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    university: Mapped[University] = relationship("University")
    target_user: Mapped[User] = relationship("User", foreign_keys=[target_user_id])
    target_student: Mapped[Student] = relationship("Student")
    device: Mapped[TrustedDevice | None] = relationship("TrustedDevice")
    actor_user: Mapped[User | None] = relationship("User", foreign_keys=[actor_user_id])
