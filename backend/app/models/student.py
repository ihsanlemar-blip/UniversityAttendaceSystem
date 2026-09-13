"""Student profile entity model representing enrolled learners."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import StudentStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class Student(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Institutional student profile entity linked 1-to-1 to a User account."""

    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint(
            "university_id",
            "student_number",
            name="uq_students_university_student_number",
        ),
        Index("ix_students_university_student_number", "university_id", "student_number"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_number: Mapped[str] = mapped_column(String(50), nullable=False)
    academic_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    admission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default=StudentStatus.ACTIVE.value,
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User")  # type: ignore[name-defined] # noqa: F821
    academic_unit: Mapped[AcademicUnit | None] = relationship(  # type: ignore[name-defined] # noqa: F821
        "AcademicUnit",
    )
    section: Mapped[Section | None] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Section",
    )
    enrollments: Mapped[list[Enrollment]] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Enrollment",
        back_populates="student",
    )

    def __repr__(self) -> str:
        return (
            f"<Student id={self.id} student_number={self.student_number} "
            f"user_id={self.user_id} status={self.status}>"
        )
