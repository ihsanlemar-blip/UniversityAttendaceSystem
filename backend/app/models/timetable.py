"""Recurring timetable weekly schedule rule model definition."""

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import TimetableStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.class_occurrence import ClassOccurrence
    from backend.app.models.course_offering import CourseOffering
    from backend.app.models.lecturer import Lecturer
    from backend.app.models.room import Room
    from backend.app.models.university import University


class Timetable(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Recurring weekly timetable schedule rule for a course offering per ADR-016."""

    __tablename__ = "timetables"
    __table_args__ = (
        CheckConstraint(
            "start_time < end_time",
            name="ck_timetables_time_range",
        ),
        CheckConstraint(
            "weekday >= 1 AND weekday <= 7",
            name="ck_timetables_weekday",
        ),
        CheckConstraint(
            "effective_from IS NULL OR effective_to IS NULL OR effective_from <= effective_to",
            name="ck_timetables_effective_range",
        ),
        Index("ix_timetables_offering_weekday", "course_offering_id", "weekday"),
        Index("ix_timetables_room_weekday", "room_id", "weekday"),
        Index("ix_timetables_lecturer_weekday", "lecturer_id", "weekday"),
        Index("ix_timetables_university_status", "university_id", "status"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    course_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("course_offerings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    lecturer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lecturers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    weekday: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    start_time: Mapped[datetime.time] = mapped_column(
        Time,
        nullable=False,
    )
    end_time: Mapped[datetime.time] = mapped_column(
        Time,
        nullable=False,
    )
    effective_from: Mapped[datetime.date | None] = mapped_column(
        Date,
        nullable=True,
    )
    effective_to: Mapped[datetime.date | None] = mapped_column(
        Date,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=TimetableStatus.ACTIVE.value,
        nullable=False,
    )

    # Relationships
    university: Mapped[University] = relationship(
        "University",
    )
    course_offering: Mapped[CourseOffering] = relationship(
        "CourseOffering",
    )
    room: Mapped[Room | None] = relationship(
        "Room",
        back_populates="timetables",
    )
    lecturer: Mapped[Lecturer | None] = relationship(
        "Lecturer",
    )
    class_occurrences: Mapped[list[ClassOccurrence]] = relationship(
        "ClassOccurrence",
        back_populates="timetable",
    )

    def __repr__(self) -> str:
        return (
            f"<Timetable id={self.id} offering_id={self.course_offering_id} "
            f"weekday={self.weekday} {self.start_time}-{self.end_time} status={self.status}>"
        )
