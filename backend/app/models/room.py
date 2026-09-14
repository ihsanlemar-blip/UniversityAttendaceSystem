"""Campus room and classroom space model definition."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import RoomStatus, RoomType
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.building import Building
    from backend.app.models.class_occurrence import ClassOccurrence
    from backend.app.models.timetable import Timetable
    from backend.app.models.university import University


class Room(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Institutional room, lab, or lecture hall located within a campus building."""

    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint(
            "building_id",
            "room_number",
            name="uq_rooms_building_room_number",
        ),
        CheckConstraint(
            "capacity IS NULL OR capacity > 0",
            name="ck_rooms_capacity_positive",
        ),
        Index("ix_rooms_university_building", "university_id", "building_id"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buildings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    room_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    capacity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    room_type: Mapped[str] = mapped_column(
        String(50),
        default=RoomType.CLASSROOM.value,
        nullable=False,
    )
    floor: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=RoomStatus.ACTIVE.value,
        nullable=False,
    )

    # Relationships
    university: Mapped[University] = relationship(
        "University",
    )
    building: Mapped[Building] = relationship(
        "Building",
        back_populates="rooms",
    )
    timetables: Mapped[list[Timetable]] = relationship(
        "Timetable",
        back_populates="room",
    )
    class_occurrences: Mapped[list[ClassOccurrence]] = relationship(
        "ClassOccurrence",
        back_populates="room",
    )

    def __repr__(self) -> str:
        return (
            f"<Room id={self.id} building_id={self.building_id} "
            f"number={self.room_number} status={self.status}>"
        )
