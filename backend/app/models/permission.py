"""Permission model for granular capability-based access control."""

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class Permission(Base, UUIDv7PrimaryKeyMixin, TimestampMixin):
    """Atomic authorization capability in resource.action format."""

    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_permissions_code"),
        Index("ix_permissions_code", "code"),
    )

    code: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    def __repr__(self) -> str:
        return f"<Permission code={self.code}>"
