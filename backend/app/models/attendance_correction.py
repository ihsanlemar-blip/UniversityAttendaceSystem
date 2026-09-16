"""Attendance operations, correction, excuse, and leave models.

Enforces INV-06 and human review workflows.
"""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import (
    CorrectionRequestStatus,
    CorrectionRequestType,
    ExcuseCategory,
    ExcuseRequestStatus,
    LeaveRequestStatus,
)
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.attendance_record import AttendanceRecord
    from backend.app.models.attendance_session import AttendanceSession
    from backend.app.models.class_occurrence import ClassOccurrence
    from backend.app.models.student import Student
    from backend.app.models.university import University
    from backend.app.models.user import User


class AttendanceCorrectionRequest(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Student attendance correction request.

    Enforces:
    - One open request rule per attendance record (via partial unique index).
    - Immutable review trail.
    - Tenant isolation via university_id.
    """

    __tablename__ = "attendance_correction_requests"
    __table_args__ = (
        Index(
            "uq_open_correction_request_per_record",
            "attendance_record_id",
            unique=True,
            postgresql_where="status IN ('PENDING', 'UNDER_REVIEW')",
        ),
        Index(
            "ix_attendance_corrections_student_status",
            "student_id",
            "status",
        ),
        Index(
            "ix_attendance_corrections_session_status",
            "attendance_session_id",
            "status",
        ),
        Index(
            "ix_attendance_corrections_university_status",
            "university_id",
            "status",
        ),
        Index(
            "ix_attendance_corrections_record_id",
            "attendance_record_id",
        ),
        Index(
            "ix_attendance_corrections_reviewer_id",
            "reviewed_by_user_id",
        ),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attendance_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attendance_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
    )
    request_type: Mapped[str] = mapped_column(
        String(50),
        default=CorrectionRequestType.OTHER.value,
        nullable=False,
    )
    requested_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    supporting_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=CorrectionRequestStatus.PENDING.value,
        nullable=False,
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_at_utc: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    university: Mapped[University] = relationship("University")
    attendance_record: Mapped[AttendanceRecord] = relationship("AttendanceRecord")
    attendance_session: Mapped[AttendanceSession] = relationship("AttendanceSession")
    student: Mapped[Student] = relationship("Student")
    reviewed_by_user: Mapped[User | None] = relationship("User", foreign_keys=[reviewed_by_user_id])

    def __repr__(self) -> str:
        return (
            f"<AttendanceCorrectionRequest id={self.id} record_id={self.attendance_record_id} "
            f"student_id={self.student_id} status={self.status}>"
        )


class AttendanceExcuseRequest(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Student attendance excuse request for an entire session or occurrence.

    Enforces:
    - One open excuse request per student per session or occurrence.
    - Categorized excuse reasons.
    - Tenant isolation.
    """

    __tablename__ = "attendance_excuse_requests"
    __table_args__ = (
        Index(
            "uq_open_excuse_request_per_session_student",
            "attendance_session_id",
            "student_id",
            unique=True,
            postgresql_where=(
                "attendance_session_id IS NOT NULL AND status IN ('PENDING', 'UNDER_REVIEW')"
            ),
        ),
        Index(
            "uq_open_excuse_request_per_occurrence_student",
            "class_occurrence_id",
            "student_id",
            unique=True,
            postgresql_where=(
                "class_occurrence_id IS NOT NULL AND status IN ('PENDING', 'UNDER_REVIEW')"
            ),
        ),
        Index(
            "ix_attendance_excuses_student_status",
            "student_id",
            "status",
        ),
        Index(
            "ix_attendance_excuses_session_status",
            "attendance_session_id",
            "status",
        ),
        Index(
            "ix_attendance_excuses_university_status",
            "university_id",
            "status",
        ),
        Index(
            "ix_attendance_excuses_record_id",
            "attendance_record_id",
        ),
        Index(
            "ix_attendance_excuses_occurrence_id",
            "class_occurrence_id",
        ),
        Index(
            "ix_attendance_excuses_reviewer_id",
            "reviewed_by_user_id",
        ),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attendance_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_records.id", ondelete="RESTRICT"),
        nullable=True,
    )
    attendance_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_sessions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    class_occurrence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("class_occurrences.id", ondelete="RESTRICT"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        default=ExcuseCategory.OTHER.value,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    document_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=ExcuseRequestStatus.PENDING.value,
        nullable=False,
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_at_utc: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    university: Mapped[University] = relationship("University")
    student: Mapped[Student] = relationship("Student")
    attendance_record: Mapped[AttendanceRecord | None] = relationship("AttendanceRecord")
    attendance_session: Mapped[AttendanceSession | None] = relationship("AttendanceSession")
    class_occurrence: Mapped[ClassOccurrence | None] = relationship("ClassOccurrence")
    reviewed_by_user: Mapped[User | None] = relationship("User", foreign_keys=[reviewed_by_user_id])

    def __repr__(self) -> str:
        return (
            f"<AttendanceExcuseRequest id={self.id} student_id={self.student_id} "
            f"category={self.category} status={self.status}>"
        )


class AttendanceLeaveRequest(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Student pre-class leave request for a scheduled class occurrence.

    Enforces:
    - One open leave request per student per class occurrence.
    - Explicit approval before occurrence.
    - Tenant isolation.
    """

    __tablename__ = "attendance_leave_requests"
    __table_args__ = (
        Index(
            "uq_open_leave_request_per_occurrence_student",
            "class_occurrence_id",
            "student_id",
            unique=True,
            postgresql_where="status IN ('PENDING', 'UNDER_REVIEW')",
        ),
        Index(
            "ix_attendance_leave_student_status",
            "student_id",
            "status",
        ),
        Index(
            "ix_attendance_leave_occurrence_status",
            "class_occurrence_id",
            "status",
        ),
        Index(
            "ix_attendance_leave_university_status",
            "university_id",
            "status",
        ),
        Index(
            "ix_attendance_leave_reviewer_id",
            "reviewed_by_user_id",
        ),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
    )
    class_occurrence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("class_occurrences.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=LeaveRequestStatus.PENDING.value,
        nullable=False,
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_at_utc: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    university: Mapped[University] = relationship("University")
    student: Mapped[Student] = relationship("Student")
    class_occurrence: Mapped[ClassOccurrence] = relationship("ClassOccurrence")
    reviewed_by_user: Mapped[User | None] = relationship("User", foreign_keys=[reviewed_by_user_id])

    def __repr__(self) -> str:
        return (
            f"<AttendanceLeaveRequest id={self.id} student_id={self.student_id} "
            f"occurrence_id={self.class_occurrence_id} status={self.status}>"
        )
