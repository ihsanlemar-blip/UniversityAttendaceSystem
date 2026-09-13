"""Common data types, standard library UUIDv7, and UTC datetime helpers."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid7

from pydantic import PlainSerializer


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


# Pydantic serializable UTC datetime type
UTCDateTime = Annotated[
    datetime,
    PlainSerializer(lambda dt: dt.isoformat(), return_type=str, when_used="json"),
]

__all__ = ["UTCDateTime", "utc_now", "uuid7"]
