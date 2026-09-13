"""Semester academic session calendar model."""

import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import RecordStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class Semester(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Institutional semester calendar session entity."""

    __tablename__ = "semesters"
    __table_args__ = (
        UniqueConstraint("academic_year_id", "code", name="uq_semesters_academic_year_code"),
        CheckConstraint("start_date < end_date", name="ck_semesters_date_range"),
        Index("ix_semesters_academic_year_id", "academic_year_id"),
        Index("ix_semesters_university_id", "university_id"),
        Index("ix_semesters_is_current", "university_id", "is_current"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=RecordStatus.ACTIVE.value,
        nullable=False,
    )

    # Relationships
    academic_year: Mapped[AcademicYear] = relationship(  # type: ignore[name-defined] # noqa: F821
        "AcademicYear",
        back_populates="semesters",
    )

    def __repr__(self) -> str:
        return (
            f"<Semester id={self.id} code={self.code} seq={self.sequence_order} "
            f"range={self.start_date}..{self.end_date} current={self.is_current}>"
        )
