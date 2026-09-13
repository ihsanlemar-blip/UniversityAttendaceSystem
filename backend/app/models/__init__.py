"""Models package exporting declarative Base and entities."""

from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin
from backend.app.models.university import University

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDv7PrimaryKeyMixin",
    "University",
]
