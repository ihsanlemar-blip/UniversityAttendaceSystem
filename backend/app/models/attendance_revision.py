"""Attendance Revision model enforcing INV-06 and INV-08."""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.common.types import utc_now
from backend.app.models.base import Base, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.attendance_record import AttendanceRecord
    from backend.app.models.attendance_session import AttendanceSession
    from backend.app.models.user import User


class AttendanceRevision(Base, UUIDv7PrimaryKeyMixin):
    """Append-only immutable audit revision ledger.

    Enforces INV-06 (corrections cannot erase history) and
    INV-08 (manual overrides require recorded justification and actor ID).
    """

    __tablename__ = "attendance_revisions"
    __table_args__ = (
        Index(
            "ix_attendance_revisions_session_event",
            "attendance_session_id",
            "event_type",
        ),
        Index(
            "ix_attendance_revisions_record_date",
            "attendance_record_id",
            "occurred_at_utc",
        ),
        Index(
            "ix_attendance_revisions_actor_date",
            "actor_user_id",
            "occurred_at_utc",
        ),
    )

    attendance_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    attendance_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_records.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    previous_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    new_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    previous_credit: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    new_credit: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    occurred_at_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    session: Mapped[AttendanceSession] = relationship(
        "AttendanceSession",
        back_populates="revisions",
    )
    attendance_record: Mapped[AttendanceRecord | None] = relationship(
        "AttendanceRecord",
        back_populates="revisions",
    )
    actor: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<AttendanceRevision id={self.id} event={self.event_type} "
            f"record_id={self.attendance_record_id} actor={self.actor_user_id}>"
        )
