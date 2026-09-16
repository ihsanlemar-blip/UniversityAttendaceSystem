"""Campus Network Presence models for Milestone 14.

Invariants Enforced:
- Campus network presence is server-observed; client claims are never authoritative.
- Network zones belong to a specific university (strict multi-tenant isolation).
- Network challenges are short-lived, cryptographically bound to student, device,
  session, checkpoint, and zone.
- Single-use challenge consumption with idempotent duplicate support.
"""

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import NetworkChallengeStatus, NetworkZoneStatus, NetworkZoneType
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.attendance_checkpoint import AttendanceCheckpoint
    from backend.app.models.attendance_session import AttendanceSession
    from backend.app.models.building import Building
    from backend.app.models.trusted_device import TrustedDevice
    from backend.app.models.university import University
    from backend.app.models.user import User


class CampusNetworkZone(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Configured campus network zone representing authorized IPv4 or IPv6 CIDR subnet.

    Can be associated with a campus building or scoped university-wide (building_id = NULL).
    """

    __tablename__ = "campus_network_zones"
    __table_args__ = (
        UniqueConstraint(
            "university_id",
            "code",
            name="uq_campus_network_zones_uni_code",
        ),
        Index(
            "ix_campus_network_zones_uni_status",
            "university_id",
            "status",
        ),
        Index(
            "ix_campus_network_zones_building_id",
            "building_id",
        ),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    building_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buildings.id", ondelete="RESTRICT"),
        nullable=True,
    )
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    network_cidr: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    ip_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=4,
    )
    zone_type: Mapped[str] = mapped_column(
        String(30),
        default=NetworkZoneType.CAMPUS_TRUSTED.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=NetworkZoneStatus.ACTIVE.value,
        nullable=False,
    )
    allow_student_presence: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    allow_lecturer_operations: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
    )

    # Relationships
    university: Mapped[University] = relationship("University")
    building: Mapped[Building | None] = relationship("Building")

    def __repr__(self) -> str:
        return (
            f"<CampusNetworkZone id={self.id} code='{self.code}' cidr='{self.network_cidr}' "
            f"type='{self.zone_type}' status='{self.status}'>"
        )


class CampusNetworkChallenge(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Short-lived presence challenge issued to an authenticated student on a registered device.

    Enforces INV-01, INV-03 (server UTC clock is authority), and single-use cryptographic binding.
    """

    __tablename__ = "campus_network_challenges"
    __table_args__ = (
        Index(
            "ix_campus_network_challenges_user_status",
            "user_id",
            "status",
        ),
        Index(
            "ix_campus_network_challenges_expiry",
            "expires_at",
            "status",
        ),
        Index(
            "ix_campus_network_challenges_session_cp",
            "attendance_session_id",
            "attendance_checkpoint_id",
        ),
        Index(
            "ix_campus_network_challenges_nonce_hash",
            "nonce_hash",
        ),
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
    trusted_device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trusted_devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attendance_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attendance_checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_checkpoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    network_zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campus_network_zones.id", ondelete="RESTRICT"),
        nullable=False,
    )
    nonce: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    nonce_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=NetworkChallengeStatus.ISSUED.value,
        nullable=False,
    )
    proof_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    issued_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    consumed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    university: Mapped[University] = relationship("University")
    user: Mapped[User] = relationship("User")
    trusted_device: Mapped[TrustedDevice] = relationship("TrustedDevice")
    session: Mapped[AttendanceSession] = relationship("AttendanceSession")
    checkpoint: Mapped[AttendanceCheckpoint] = relationship("AttendanceCheckpoint")
    network_zone: Mapped[CampusNetworkZone] = relationship("CampusNetworkZone")

    def __repr__(self) -> str:
        return (
            f"<CampusNetworkChallenge id={self.id} user_id={self.user_id} "
            f"zone_id={self.network_zone_id} status='{self.status}' expires_at={self.expires_at}>"
        )
