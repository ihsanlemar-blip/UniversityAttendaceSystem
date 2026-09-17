"""Course offering model representing semester-specific course delivery."""

import uuid

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import OfferingStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class CourseOffering(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Institutional course offering delivery instance coupling Course + Semester + Section."""

    __tablename__ = "course_offerings"
    __table_args__ = (
        Index("ix_course_offerings_course_semester", "course_id", "semester_id"),
        Index(
            "uq_course_offerings_with_section",
            "university_id",
            "course_id",
            "semester_id",
            "section_id",
            unique=True,
            postgresql_where=text("section_id IS NOT NULL"),
        ),
        Index(
            "uq_course_offerings_without_section",
            "university_id",
            "course_id",
            "semester_id",
            unique=True,
            postgresql_where=text("section_id IS NULL"),
        ),
        Index(
            "ix_course_offerings_semester_status",
            "semester_id",
            "status",
        ),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    semester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semesters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    academic_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_units.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=OfferingStatus.ACTIVE.value,
        nullable=False,
    )

    # Relationships
    course: Mapped[Course] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Course",
        back_populates="offerings",
    )
    semester: Mapped[Semester] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Semester",
    )
    section: Mapped[Section | None] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Section",
        back_populates="offerings",
    )
    academic_unit: Mapped[AcademicUnit | None] = relationship(  # type: ignore[name-defined] # noqa: F821
        "AcademicUnit",
    )
    lecturer_assignments: Mapped[list[LecturerAssignment]] = relationship(  # type: ignore[name-defined] # noqa: F821
        "LecturerAssignment",
        back_populates="course_offering",
        cascade="all, delete-orphan",
    )
    enrollments: Mapped[list[Enrollment]] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Enrollment",
        back_populates="course_offering",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<CourseOffering id={self.id} course_id={self.course_id} "
            f"semester_id={self.semester_id} section_id={self.section_id} status={self.status}>"
        )
