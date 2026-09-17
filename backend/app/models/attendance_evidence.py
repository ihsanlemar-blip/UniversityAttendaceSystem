"""Attendance Evidence model definition enforcing INV-01 and INV-05."""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.common.types import utc_now
from backend.app.core.constants import EvidenceSourceMode
from backend.app.models.base import Base, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.attendance_checkpoint import AttendanceCheckpoint
    from backend.app.models.student import Student
    from backend.app.models.user import User


class AttendanceEvidence(Base, UUIDv7PrimaryKeyMixin):
    """Append-only verification evidence submitted for an attendance checkpoint.

    Enforces INV-01 (client cannot mark itself present; only server verifies evidence)
    and INV-05 (unique checkpoint_id + student_id guarantees no duplicate credit).
    """

    __tablename__ = "attendance_evidence"
    __table_args__ = (
        UniqueConstraint(
            "attendance_checkpoint_id",
            "student_id",
            name="uq_attendance_evidence_checkpoint_student",
        ),
        Index(
            "ix_attendance_evidence_student_received",
            "student_id",
            "server_received_at_utc",
        ),
        Index(
            "ix_attendance_evidence_checkpoint_student",
            "attendance_checkpoint_id",
            "student_id",
        ),
        Index(
            "ix_attendance_evidence_checkpoint_source",
            "attendance_checkpoint_id",
            "source_mode",
        ),
    )

    attendance_checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_checkpoints.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    submitted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_mode: Mapped[str] = mapped_column(
        String(30),
        default=EvidenceSourceMode.MANUAL.value,
        nullable=False,
    )
    server_received_at_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    manual_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    evidence_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    checkpoint: Mapped[AttendanceCheckpoint] = relationship(
        "AttendanceCheckpoint",
        back_populates="evidence_list",
    )
    student: Mapped[Student] = relationship("Student")
    submitted_by_user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<AttendanceEvidence id={self.id} checkpoint_id={self.attendance_checkpoint_id} "
            f"student_id={self.student_id} source={self.source_mode}>"
        )
