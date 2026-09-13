"""Base declarative models and schema conventions for SQLAlchemy 2.0."""

import uuid
from datetime import datetime

from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from backend.app.common.types import utc_now, uuid7

# Predictable naming convention for database constraints and indexes
POSTGRESQL_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_`%(constraint_name)s`",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarative class for all application models."""

    metadata = MetaData(naming_convention=POSTGRESQL_NAMING_CONVENTION)


class TimestampMixin:
    """Mixin adding created_at and updated_at UTC timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class UUIDv7PrimaryKeyMixin:
    """Mixin providing an indexed, sequential UUIDv7 primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
        index=True,
    )
