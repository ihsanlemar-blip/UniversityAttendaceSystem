"""Course catalog entity model representing institutional curriculum."""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import RecordStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class Course(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Institutional course master catalog entity."""

    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("university_id", "code", name="uq_courses_university_code"),
        Index("ix_courses_university_code", "university_id", "code"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_units.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    credit_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default=RecordStatus.ACTIVE.value,
        nullable=False,
    )

    # Relationships
    academic_unit: Mapped[AcademicUnit | None] = relationship(  # type: ignore[name-defined] # noqa: F821
        "AcademicUnit",
    )
    offerings: Mapped[list[CourseOffering]] = relationship(  # type: ignore[name-defined] # noqa: F821
        "CourseOffering",
        back_populates="course",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Course id={self.id} code={self.code} name={self.name} status={self.status}>"
