"""Section model representing student cohorts / groups."""

import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import RecordStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class Section(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Institutional student cohort / section grouping."""

    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint(
            "university_id",
            "semester_id",
            "code",
            name="uq_sections_university_semester_code",
        ),
        Index("ix_sections_university_code", "university_id", "code"),
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
    semester_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semesters.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=RecordStatus.ACTIVE.value,
        nullable=False,
    )

    # Relationships
    academic_unit: Mapped[AcademicUnit | None] = relationship(  # type: ignore[name-defined] # noqa: F821
        "AcademicUnit",
    )
    semester: Mapped[Semester | None] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Semester",
    )
    offerings: Mapped[list[CourseOffering]] = relationship(  # type: ignore[name-defined] # noqa: F821
        "CourseOffering",
        back_populates="section",
    )

    def __repr__(self) -> str:
        return (
            f"<Section id={self.id} code={self.code} name={self.name} "
            f"semester_id={self.semester_id}>"
        )
