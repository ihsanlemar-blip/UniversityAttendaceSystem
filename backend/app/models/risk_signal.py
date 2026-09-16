"""Attendance Risk Signal model definition for Milestone 14 Anti-Cheat Hardening.

Invariants Enforced:
- Anti-cheat signals are explainable, factorized, and versioned records.
- Signals are strictly review information for human administrators (INV-01, Section 1 & 3).
- Signals NEVER automatically modify attendance records or apply student/lecturer punishment.
- Idempotency is guaranteed via unique risk_key per university.
"""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.common.types import utc_now
from backend.app.core.constants import RiskSeverity, RiskSignalStatus, RiskSubjectType
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.attendance_session import AttendanceSession
    from backend.app.models.class_occurrence import ClassOccurrence
    from backend.app.models.course_offering import CourseOffering
    from backend.app.models.trusted_device import TrustedDevice
    from backend.app.models.university import University
    from backend.app.models.user import User


class AttendanceRiskSignal(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Durable, explainable anti-cheat risk signal logged for human administrative review."""

    __tablename__ = "attendance_risk_signals"
    __table_args__ = (
        UniqueConstraint(
            "university_id",
            "risk_key",
            name="uq_attendance_risk_signals_key",
        ),
        Index(
            "ix_attendance_risk_signals_uni_status",
            "university_id",
            "status",
            "detected_at",
        ),
        Index(
            "ix_attendance_risk_signals_type_sev",
            "university_id",
            "signal_type",
            "severity",
        ),
        Index(
            "ix_attendance_risk_signals_subject_user",
            "subject_user_id",
        ),
        Index(
            "ix_attendance_risk_signals_session",
            "attendance_session_id",
        ),
        Index(
            "ix_attendance_risk_signals_occurrence",
            "class_occurrence_id",
        ),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    signal_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        default=RiskSeverity.INFO.value,
        nullable=False,
    )
    risk_points: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    subject_type: Mapped[str] = mapped_column(
        String(30),
        default=RiskSubjectType.STUDENT.value,
        nullable=False,
    )
    subject_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    trusted_device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trusted_devices.id", ondelete="SET NULL"),
        nullable=True,
    )
    attendance_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    class_occurrence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("class_occurrences.id", ondelete="SET NULL"),
        nullable=True,
    )
    course_offering_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("course_offerings.id", ondelete="SET NULL"),
        nullable=True,
    )
    context: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    rule_version: Mapped[str] = mapped_column(
        String(20),
        default="1.0",
        nullable=False,
    )
    risk_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    detected_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=RiskSignalStatus.OPEN.value,
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
        String(1000),
        nullable=True,
    )
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    university: Mapped[University] = relationship("University")
    subject_user: Mapped[User | None] = relationship("User", foreign_keys=[subject_user_id])
    reviewed_by_user: Mapped[User | None] = relationship("User", foreign_keys=[reviewed_by_user_id])
    trusted_device: Mapped[TrustedDevice | None] = relationship("TrustedDevice")
    session: Mapped[AttendanceSession | None] = relationship("AttendanceSession")
    occurrence: Mapped[ClassOccurrence | None] = relationship("ClassOccurrence")
    offering: Mapped[CourseOffering | None] = relationship("CourseOffering")

    def __repr__(self) -> str:
        return (
            f"<AttendanceRiskSignal id={self.id} type='{self.signal_type}' "
            f"severity='{self.severity}' status='{self.status}' key='{self.risk_key}'>"
        )
