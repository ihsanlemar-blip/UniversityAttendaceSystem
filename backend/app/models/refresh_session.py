"""Refresh session model with cryptographic token hash and family rotation."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class RefreshSession(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Server-side persistent session record backing high-entropy refresh tokens.

    Invariants:
    1. Raw refresh token is NEVER stored; only SHA-256 hash (token_hash) is persisted.
    2. Rotation links child sessions via family_id and replaced_by_id.
    3. Replay detection: If an already-revoked session is presented, the entire
       family_id chain is immediately revoked.
    """

    __tablename__ = "refresh_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_sessions_token_hash"),
        Index("ix_refresh_sessions_user_id", "user_id"),
        Index("ix_refresh_sessions_family_id", "family_id"),
        Index("ix_refresh_sessions_token_hash", "token_hash"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revocation_reason: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refresh_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    @property
    def is_expired(self) -> bool:
        """Return True if session has expired."""
        from backend.app.common.types import utc_now

        return self.expires_at <= utc_now()

    @property
    def is_active(self) -> bool:
        """Return True if session is not revoked and not expired."""
        return self.revoked_at is None and not self.is_expired

    def __repr__(self) -> str:
        return f"<RefreshSession id={self.id} user_id={self.user_id} active={self.is_active}>"
