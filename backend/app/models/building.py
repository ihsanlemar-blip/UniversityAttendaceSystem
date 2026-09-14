"""Campus building model definition."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import BuildingStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.room import Room
    from backend.app.models.university import University


class Building(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Institutional campus building housing classrooms, lecture halls, and offices."""

    __tablename__ = "buildings"
    __table_args__ = (
        UniqueConstraint(
            "university_id",
            "code",
            name="uq_buildings_university_code",
        ),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=BuildingStatus.ACTIVE.value,
        nullable=False,
    )

    # Relationships
    university: Mapped[University] = relationship(
        "University",
    )
    rooms: Mapped[list[Room]] = relationship(
        "Room",
        back_populates="building",
    )

    def __repr__(self) -> str:
        return f"<Building code={self.code} name={self.name} status={self.status}>"
