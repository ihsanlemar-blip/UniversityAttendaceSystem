"""Concrete calendar class occurrence model definition per ADR-016."""

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import ClassOccurrenceStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.course_offering import CourseOffering
    from backend.app.models.lecturer import Lecturer
    from backend.app.models.room import Room
    from backend.app.models.timetable import Timetable
    from backend.app.models.university import University


class ClassOccurrence(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Concrete calendar instance of a scheduled class meeting on a specific date per ADR-016.

    This model serves as the future parent anchor for AttendanceSession (Milestone 9+).
    """

    __tablename__ = "class_occurrences"
    __table_args__ = (
        CheckConstraint(
            "scheduled_start_utc < scheduled_end_utc",
            name="ck_class_occurrences_time_range",
        ),
        Index(
            "uq_class_occurrences_timetable_start",
            "timetable_id",
            "scheduled_start_utc",
            unique=True,
            postgresql_where=text("timetable_id IS NOT NULL"),
        ),
        Index(
            "ix_class_occurrences_offering_start",
            "course_offering_id",
            "scheduled_start_utc",
        ),
        Index(
            "ix_class_occurrences_room_start",
            "room_id",
            "scheduled_start_utc",
        ),
        Index(
            "ix_class_occurrences_lecturer_start",
            "lecturer_id",
            "scheduled_start_utc",
        ),
        Index(
            "ix_class_occurrences_start_status",
            "scheduled_start_utc",
            "status",
        ),
        Index(
            "ix_class_occurrences_local_date",
            "university_id",
            "local_date",
        ),
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
    timetable_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("timetables.id", ondelete="SET NULL"),
        nullable=True,
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
    substitute_lecturer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lecturers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    local_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
    )
    scheduled_start_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    scheduled_end_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=ClassOccurrenceStatus.SCHEDULED.value,
        nullable=False,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    rescheduled_from_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("class_occurrences.id", ondelete="SET NULL"),
        nullable=True,
    )
    rescheduled_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("class_occurrences.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    university: Mapped[University] = relationship(
        "University",
    )
    course_offering: Mapped[CourseOffering] = relationship(
        "CourseOffering",
    )
    timetable: Mapped[Timetable | None] = relationship(
        "Timetable",
        back_populates="class_occurrences",
    )
    room: Mapped[Room | None] = relationship(
        "Room",
        back_populates="class_occurrences",
    )
    lecturer: Mapped[Lecturer | None] = relationship(
        "Lecturer",
        foreign_keys=[lecturer_id],
    )
    substitute_lecturer: Mapped[Lecturer | None] = relationship(
        "Lecturer",
        foreign_keys=[substitute_lecturer_id],
    )
    rescheduled_from: Mapped[ClassOccurrence | None] = relationship(
        "ClassOccurrence",
        remote_side="ClassOccurrence.id",
        foreign_keys=[rescheduled_from_id],
    )

    def __repr__(self) -> str:
        return (
            f"<ClassOccurrence id={self.id} offering_id={self.course_offering_id} "
            f"date={self.local_date} start={self.scheduled_start_utc} status={self.status}>"
        )
