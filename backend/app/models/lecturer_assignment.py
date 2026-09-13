"""Lecturer assignment model connecting instructors to course offerings."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import LecturerAssignmentType, RecordStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class LecturerAssignment(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Assignment connecting an instructor / lecturer to a specific course offering."""

    __tablename__ = "lecturer_assignments"
    __table_args__ = (
        UniqueConstraint(
            "course_offering_id",
            "lecturer_id",
            name="uq_lecturer_assignments_offering_lecturer",
        ),
        Index(
            "uq_primary_lecturer_per_offering",
            "course_offering_id",
            unique=True,
            postgresql_where=text("is_primary = true"),
        ),
    )

    course_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("course_offerings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lecturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lecturers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    assignment_type: Mapped[str] = mapped_column(
        String(30),
        default=LecturerAssignmentType.PRIMARY.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=RecordStatus.ACTIVE.value,
        nullable=False,
    )

    # Relationships
    course_offering: Mapped[CourseOffering] = relationship(  # type: ignore[name-defined] # noqa: F821
        "CourseOffering",
        back_populates="lecturer_assignments",
    )
    lecturer: Mapped[Lecturer] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Lecturer",
        back_populates="assignments",
    )

    def __repr__(self) -> str:
        return (
            f"<LecturerAssignment id={self.id} offering_id={self.course_offering_id} "
            f"lecturer_id={self.lecturer_id} is_primary={self.is_primary}>"
        )
