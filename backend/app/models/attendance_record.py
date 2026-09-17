"""Attendance Record model definition per ADR-016 and PRD Section 6."""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import AttendanceStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.attendance_revision import AttendanceRevision
    from backend.app.models.attendance_session import AttendanceSession
    from backend.app.models.student import Student


class AttendanceRecord(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Session-level student attendance outcome.

    Initialized in PENDING status upon session activation as part of the frozen roster.
    Final status evaluated upon session completion or manual administrative action.
    """

    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint(
            "attendance_session_id",
            "student_id",
            name="uq_attendance_records_session_student",
        ),
        Index(
            "ix_attendance_records_session_status",
            "attendance_session_id",
            "status",
        ),
        Index(
            "ix_attendance_records_student_status",
            "student_id",
            "status",
        ),
        Index(
            "ix_attendance_records_student_created",
            "student_id",
            "created_at",
        ),
    )

    attendance_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=AttendanceStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    start_credited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    middle_credited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    end_credited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    checkpoints_verified: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    attendance_credit: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0.0,
        nullable=False,
    )
    is_manual: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    manual_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    calculation_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    finalized_at_utc: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    version_no: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    # Relationships
    session: Mapped[AttendanceSession] = relationship(
        "AttendanceSession",
        back_populates="records",
    )
    student: Mapped[Student] = relationship("Student")
    revisions: Mapped[list[AttendanceRevision]] = relationship(
        "AttendanceRevision",
        back_populates="attendance_record",
        cascade="all, delete-orphan",
        order_by="AttendanceRevision.occurred_at_utc",
    )

    def __repr__(self) -> str:
        return (
            f"<AttendanceRecord id={self.id} session_id={self.attendance_session_id} "
            f"student_id={self.student_id} status={self.status} credit={self.attendance_credit}>"
        )
