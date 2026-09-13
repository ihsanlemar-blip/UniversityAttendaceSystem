"""Academic unit model supporting flexible self-referential hierarchy per ADR-017."""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import AcademicUnitType, RecordStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class AcademicUnit(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Institutional academic organizational unit entity.

    Per ADR-017, models flexible hierarchy (e.g. Faculty -> Department -> Program
    or Faculty -> Program) without forcing intermediate tiers.
    """

    __tablename__ = "academic_units"
    __table_args__ = (
        UniqueConstraint("university_id", "code", name="uq_academic_units_university_code"),
        Index("ix_academic_units_university_parent", "university_id", "parent_id"),
        Index("ix_academic_units_university_type", "university_id", "unit_type"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_units.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    unit_type: Mapped[str] = mapped_column(
        String(30),
        default=AcademicUnitType.FACULTY.value,
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default=RecordStatus.ACTIVE.value,
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    parent: Mapped[AcademicUnit | None] = relationship(
        "AcademicUnit",
        remote_side="AcademicUnit.id",
        back_populates="children",
        foreign_keys=[parent_id],
    )
    children: Mapped[list[AcademicUnit]] = relationship(
        "AcademicUnit",
        back_populates="parent",
        foreign_keys=[parent_id],
    )

    def __repr__(self) -> str:
        return (
            f"<AcademicUnit id={self.id} code={self.code} "
            f"type={self.unit_type} parent_id={self.parent_id}>"
        )
