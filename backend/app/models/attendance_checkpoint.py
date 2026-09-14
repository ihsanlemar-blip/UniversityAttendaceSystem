"""Attendance Checkpoint model definition per approved 3-checkpoint architecture."""

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import AttendanceCheckpointStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.attendance_evidence import AttendanceEvidence
    from backend.app.models.attendance_session import AttendanceSession
    from backend.app.models.user import User


class AttendanceCheckpoint(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Discrete attendance verification window inside an AttendanceSession.

    Architecture strictly requires exactly three checkpoints: START, MIDDLE, END.
    Alternative models (FIRST_HALF, SECOND_HALF, RANDOM_POP) are strictly prohibited.
    """

    __tablename__ = "attendance_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "attendance_session_id",
            "checkpoint_type",
            name="uq_attendance_checkpoints_session_type",
        ),
        UniqueConstraint(
            "attendance_session_id",
            "sequence_no",
            name="uq_attendance_checkpoints_session_seq",
        ),
        CheckConstraint(
            "checkpoint_type IN ('START', 'MIDDLE', 'END')",
            name="ck_attendance_checkpoints_type",
        ),
        CheckConstraint(
            "sequence_no IN (1, 2, 3)",
            name="ck_attendance_checkpoints_sequence",
        ),
        Index(
            "ix_attendance_checkpoints_session_status",
            "attendance_session_id",
            "status",
        ),
    )

    attendance_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    checkpoint_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    sequence_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=AttendanceCheckpointStatus.SCHEDULED.value,
        nullable=False,
    )
    window_duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=300,
        nullable=False,
    )
    opened_at_utc: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_at_utc: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    opened_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    # Relationships
    session: Mapped[AttendanceSession] = relationship(
        "AttendanceSession",
        back_populates="checkpoints",
    )
    opened_by_user: Mapped[User | None] = relationship("User", foreign_keys=[opened_by_user_id])
    closed_by_user: Mapped[User | None] = relationship("User", foreign_keys=[closed_by_user_id])
    evidence_list: Mapped[list[AttendanceEvidence]] = relationship(
        "AttendanceEvidence",
        back_populates="checkpoint",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<AttendanceCheckpoint id={self.id} type={self.checkpoint_type} "
            f"seq={self.sequence_no} status={self.status}>"
        )
