"""Lecturer profile entity model representing academic instructors."""

import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import LecturerStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class Lecturer(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Institutional lecturer / instructor profile entity linked 1-to-1 to a User account."""

    __tablename__ = "lecturers"
    __table_args__ = (
        UniqueConstraint(
            "university_id",
            "employee_code",
            name="uq_lecturers_university_employee_code",
        ),
        Index("ix_lecturers_university_employee_code", "university_id", "employee_code"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
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
    employee_code: Mapped[str] = mapped_column(String(50), nullable=False)
    academic_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default=LecturerStatus.ACTIVE.value,
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User")  # type: ignore[name-defined] # noqa: F821
    academic_unit: Mapped[AcademicUnit | None] = relationship(  # type: ignore[name-defined] # noqa: F821
        "AcademicUnit",
    )
    assignments: Mapped[list[LecturerAssignment]] = relationship(  # type: ignore[name-defined] # noqa: F821
        "LecturerAssignment",
        back_populates="lecturer",
    )

    def __repr__(self) -> str:
        return (
            f"<Lecturer id={self.id} employee_code={self.employee_code} "
            f"user_id={self.user_id} title={self.title}>"
        )
