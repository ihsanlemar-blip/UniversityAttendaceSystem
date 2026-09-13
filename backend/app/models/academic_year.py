"""Academic year calendar model."""

import uuid
from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import RecordStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class AcademicYear(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Institutional academic year period entity."""

    __tablename__ = "academic_years"
    __table_args__ = (
        UniqueConstraint("university_id", "code", name="uq_academic_years_university_code"),
        CheckConstraint("start_date < end_date", name="ck_academic_years_date_range"),
        Index("ix_academic_years_university_id", "university_id"),
        Index("ix_academic_years_is_current", "university_id", "is_current"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=RecordStatus.ACTIVE.value,
        nullable=False,
    )

    # Relationships
    semesters: Mapped[list[Semester]] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Semester",
        back_populates="academic_year",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<AcademicYear id={self.id} code={self.code} "
            f"range={self.start_date}..{self.end_date} current={self.is_current}>"
        )
