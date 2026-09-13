"""User identity model for authentication and account state."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.constants import DEFAULT_LOCALE, UserStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class User(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """User account entity.

    Represents an authenticated identity. Specific academic or administrative
    profiles (Students, Lecturers) link to this user account in later milestones.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("university_id", "username", name="uq_users_university_id_username"),
        Index("ix_users_username", "username"),
        Index("ix_users_university_id", "university_id"),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
    )
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferred_language: Mapped[str] = mapped_column(
        String(10),
        default=DEFAULT_LOCALE,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=UserStatus.ACTIVE.value,
        nullable=False,
    )
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username} status={self.status}>"
