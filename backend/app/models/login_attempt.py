"""Login attempt security tracking model for rate limiting and anomaly detection."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.common.types import utc_now
from backend.app.models.base import Base, UUIDv7PrimaryKeyMixin


class LoginAttempt(Base, UUIDv7PrimaryKeyMixin):
    """Security audit record for authentication attempts.

    Used to detect brute-force activity, trigger temporary account lockouts,
    and preserve non-sensitive telemetry without logging credentials.
    """

    __tablename__ = "login_attempts"
    __table_args__ = (
        Index("ix_login_attempts_normalized_username", "normalized_username"),
        Index("ix_login_attempts_created_at", "created_at"),
        Index("ix_login_attempts_university_id", "university_id"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    normalized_username: Mapped[str] = mapped_column(String(50), nullable=False)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason_internal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<LoginAttempt id={self.id} "
            f"username={self.normalized_username} success={self.success}>"
        )
