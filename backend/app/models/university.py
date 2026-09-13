"""University institutional model definition."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.constants import DEFAULT_LOCALE, DEFAULT_TIMEZONE, RecordStatus
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class University(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """University institution entity.

    Per ADR-021, Version 1 is single-university operational authority,
    but retains university_id boundaries for institutional isolation.
    """

    __tablename__ = "universities"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(50), default=DEFAULT_TIMEZONE, nullable=False)
    default_language: Mapped[str] = mapped_column(
        String(10), default=DEFAULT_LOCALE, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=RecordStatus.ACTIVE.value, nullable=False
    )

    def __repr__(self) -> str:
        return f"<University code={self.code} name={self.name}>"
