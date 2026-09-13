"""Student enrollment entity model connecting students to course offerings."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import EnrollmentStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class Enrollment(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Institutional student course offering enrollment record."""

    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint(
            "course_offering_id",
            "student_id",
            name="uq_enrollments_offering_student",
        ),
        Index("ix_enrollments_status", "status"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("course_offerings.id", ondelete="CASCADE"),
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
        default=EnrollmentStatus.ACTIVE.value,
        nullable=False,
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    dropped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    course_offering: Mapped[CourseOffering] = relationship(  # type: ignore[name-defined] # noqa: F821
        "CourseOffering",
        back_populates="enrollments",
    )
    student: Mapped[Student] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Student",
        back_populates="enrollments",
    )

    def __repr__(self) -> str:
        return (
            f"<Enrollment id={self.id} offering_id={self.course_offering_id} "
            f"student_id={self.student_id} status={self.status}>"
        )
