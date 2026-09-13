"""Unit tests for common types: RFC 9562 UUIDv7 and UTC datetime helpers."""

import time
import uuid
from datetime import UTC

from backend.app.common.types import utc_now, uuid7


def test_uuid7_version_and_variant() -> None:
    """Verify generated UUIDv7 has version 7 and RFC 4122 variant."""
    val = uuid7()
    assert isinstance(val, uuid.UUID)
    assert val.version == 7
    # Variant should be RFC 4122 (0b10..)
    assert val.variant == uuid.RFC_4122


def test_uuid7_time_ordering() -> None:
    """Verify successive UUIDv7 identifiers are chronologically sortable."""
    uuids = []
    for _ in range(10):
        uuids.append(uuid7())
        time.sleep(0.002)  # ensure 2ms between ticks

    sorted_uuids = sorted(uuids)
    assert uuids == sorted_uuids


def test_utc_now_timezone_aware() -> None:
    """Verify utc_now() returns timezone-aware UTC datetime."""
    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo == UTC
