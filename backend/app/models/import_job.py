"""Data import job and row staging models.

Enforces:
- Staged preview and row validation prior to any production mutation.
- Tenant isolation via university_id.
- Auditability and idempotency.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.constants import (
    ImportCommitMode,
    ImportJobStatus,
    ImportRowAction,
    ImportRowStatus,
)
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.university import University
    from backend.app.models.user import User


class ImportJob(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Import job header tracking file metadata, validation state, and commit status."""

    __tablename__ = "import_jobs"
    __table_args__ = (
        Index("ix_import_jobs_uni_type_status", "university_id", "import_type", "status"),
        Index("ix_import_jobs_uni_created", "university_id", "created_at"),
        Index("ix_import_jobs_idempotency", "idempotency_key"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    import_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ImportJobStatus.UPLOADED.value,
        index=True,
    )
    commit_mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ImportCommitMode.STRICT.value,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    row_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    valid_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    warning_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    error_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    commit_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    university: Mapped[University] = relationship(
        "University",
        foreign_keys=[university_id],
        lazy="selectin",
    )
    requested_by: Mapped[User] = relationship(
        "User",
        foreign_keys=[requested_by_user_id],
        lazy="selectin",
    )
    rows: Mapped[list[ImportRow]] = relationship(
        "ImportRow",
        back_populates="import_job",
        cascade="all, delete-orphan",
        order_by="ImportRow.row_number",
        lazy="selectin",
    )


class ImportRow(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Staged row data representing an individual record from an import file."""

    __tablename__ = "import_rows"
    __table_args__ = (
        UniqueConstraint("import_job_id", "row_number", name="uq_import_rows_job_row_number"),
        Index("ix_import_rows_job_status", "import_job_id", "status"),
    )

    import_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    normalized_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ImportRowAction.CREATE.value,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ImportRowStatus.VALID.value,
        index=True,
    )
    errors: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    warnings: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    resolved_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    resolved_entity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Relationships
    import_job: Mapped[ImportJob] = relationship(
        "ImportJob",
        back_populates="rows",
    )
