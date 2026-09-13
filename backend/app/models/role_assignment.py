"""Role assignment model with organizational scope and revocation history."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.common.types import utc_now
from backend.app.core.constants import ScopeType
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class RoleAssignment(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Scoped assignment of a role to a user.

    In Milestone 5, scope_type is strictly UNIVERSITY, with scope_id referencing
    the university_id. Revoking an assignment retains the record with revoked_at
    and revocation_reason populated to preserve historical auditability.
    """

    __tablename__ = "role_assignments"
    __table_args__ = (
        Index("ix_role_assignments_user_id", "user_id"),
        Index("ix_role_assignments_role_id", "role_id"),
        Index("ix_role_assignments_university_id", "university_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope_type: Mapped[str] = mapped_column(
        String(50),
        default=ScopeType.UNIVERSITY.value,
        nullable=False,
    )
    scope_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    revocation_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<RoleAssignment id={self.id} user_id={self.user_id} "
            f"role_id={self.role_id} scope={self.scope_type}:{self.scope_id}>"
        )
