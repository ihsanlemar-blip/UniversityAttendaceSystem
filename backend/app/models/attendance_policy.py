"""Attendance Policy model definition per PRD Section 6 and ADR-016."""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import PolicyScopeType, RecordStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.academic_unit import AcademicUnit
    from backend.app.models.course import Course
    from backend.app.models.university import University


DEFAULT_CHECKPOINT_WEIGHTS: dict[str, float] = {
    "START": 1.0,
    "MIDDLE": 1.0,
    "END": 1.0,
}

DEFAULT_STATUS_MAPPING: dict[str, str] = {
    "111": "PRESENT",
    "110": "PRESENT",
    "101": "PRESENT",
    "011": "LATE",
    "100": "LATE",
    "010": "LATE",
    "001": "ABSENT",
    "000": "ABSENT",
}


class AttendancePolicy(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Configurable attendance policy supporting hierarchical precedence resolution:

    Course override -> Program override -> Faculty override -> University default.
    """

    __tablename__ = "attendance_policies"
    __table_args__ = (
        CheckConstraint(
            "min_attendance_percentage >= 0 AND min_attendance_percentage <= 100",
            name="ck_attendance_policies_min_pct",
        ),
        CheckConstraint(
            "checkpoint_duration_seconds >= 60 AND checkpoint_duration_seconds <= 3600",
            name="ck_attendance_policies_duration",
        ),
        CheckConstraint(
            "late_threshold_minutes >= 0 AND late_threshold_minutes <= 120",
            name="ck_attendance_policies_late_thresh",
        ),
        Index(
            "ix_attendance_policies_scope_lookup",
            "university_id",
            "scope_type",
            "scope_id",
        ),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    academic_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_units.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    scope_type: Mapped[str] = mapped_column(
        String(20),
        default=PolicyScopeType.UNIVERSITY.value,
        nullable=False,
    )
    scope_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    min_attendance_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=75.0,
        nullable=False,
    )
    late_threshold_minutes: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )
    lecturer_correction_window_hours: Mapped[int] = mapped_column(
        Integer,
        default=24,
        nullable=False,
    )
    required_checkpoint_count: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )
    checkpoint_duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=300,
        nullable=False,
    )
    token_rotation_seconds: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
    )
    checkpoint_weights: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: dict(DEFAULT_CHECKPOINT_WEIGHTS),
        nullable=False,
    )
    status_mapping: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: dict(DEFAULT_STATUS_MAPPING),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=RecordStatus.ACTIVE.value,
        nullable=False,
    )
    effective_from: Mapped[datetime.date | None] = mapped_column(
        Date,
        nullable=True,
    )
    effective_to: Mapped[datetime.date | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Relationships
    university: Mapped[University] = relationship("University")
    academic_unit: Mapped[AcademicUnit | None] = relationship("AcademicUnit")
    course: Mapped[Course | None] = relationship("Course")

    def __repr__(self) -> str:
        return (
            f"<AttendancePolicy id={self.id} name='{self.name}' "
            f"scope={self.scope_type} min_pct={self.min_attendance_percentage}>"
        )
