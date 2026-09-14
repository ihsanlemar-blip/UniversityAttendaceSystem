"""Attendance Session model definition per PRD Section 6 and ADR-016."""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from backend.app.core.constants import AttendanceSessionStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.attendance_checkpoint import AttendanceCheckpoint
    from backend.app.models.attendance_policy import AttendancePolicy
    from backend.app.models.attendance_record import AttendanceRecord
    from backend.app.models.attendance_revision import AttendanceRevision
    from backend.app.models.class_occurrence import ClassOccurrence
    from backend.app.models.university import University
    from backend.app.models.user import User


class AttendanceSession(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Attendance operational session anchored 1:1 to a concrete ClassOccurrence.

    Enforces INV-01, INV-02, and INV-03 (server UTC clock is authoritative).
    """

    __tablename__ = "attendance_sessions"
    __table_args__ = (
        Index(
            "ix_attendance_sessions_status_occurrence",
            "status",
            "class_occurrence_id",
        ),
        Index(
            "ix_attendance_sessions_university_status",
            "university_id",
            "status",
        ),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    class_occurrence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("class_occurrences.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    attendance_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_policies.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=AttendanceSessionStatus.SCHEDULED.value,
        nullable=False,
        index=True,
    )
    host_type: Mapped[str] = mapped_column(
        String(30),
        default="LOCAL_SERVER",
        nullable=False,
    )
    opened_at_utc: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    paused_at_utc: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resumed_at_utc: Mapped[datetime.datetime | None] = mapped_column(
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
    university: Mapped[University] = relationship("University")
    class_occurrence: Mapped[ClassOccurrence] = relationship(
        "ClassOccurrence",
        backref=backref("attendance_session", uselist=False),
    )
    attendance_policy: Mapped[AttendancePolicy | None] = relationship("AttendancePolicy")
    opened_by_user: Mapped[User | None] = relationship("User", foreign_keys=[opened_by_user_id])
    closed_by_user: Mapped[User | None] = relationship("User", foreign_keys=[closed_by_user_id])

    checkpoints: Mapped[list[AttendanceCheckpoint]] = relationship(
        "AttendanceCheckpoint",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AttendanceCheckpoint.sequence_no",
    )
    records: Mapped[list[AttendanceRecord]] = relationship(
        "AttendanceRecord",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    revisions: Mapped[list[AttendanceRevision]] = relationship(
        "AttendanceRevision",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AttendanceRevision.occurred_at_utc",
    )

    def __repr__(self) -> str:
        return (
            f"<AttendanceSession id={self.id} occurrence_id={self.class_occurrence_id} "
            f"status={self.status} opened_at={self.opened_at_utc}>"
        )
