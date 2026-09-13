"""Common data types, UUIDv7 generation, and UTC datetime helpers."""

import os
import time
import uuid
from datetime import UTC, datetime
from typing import Annotated

from pydantic import PlainSerializer


def uuid7() -> uuid.UUID:
    """Generate an RFC 9562 compliant UUIDv7.

    UUIDv7 encodes Unix timestamp in milliseconds in the leading 48 bits,
    providing monotonic, index-friendly sequential primary keys for PostgreSQL.
    """
    ns = time.time_ns()
    ms = ns // 1_000_000
    rand_bytes = os.urandom(10)

    # 48 bits timestamp (ms)
    time_high = (ms >> 16) & 0xFFFFFFFF
    time_mid = ms & 0xFFFF

    # 12 bits random + 4 bits version (0b0111 = 7)
    time_low_and_version = ((rand_bytes[0] & 0x0F) | 0x70) << 8 | rand_bytes[1]

    # 2 bits variant (0b10) + 62 bits random
    clk_seq_hi_res = (rand_bytes[2] & 0x3F) | 0x80
    clk_seq_low = rand_bytes[3]
    node = int.from_bytes(rand_bytes[4:], byteorder="big")

    return uuid.UUID(
        fields=(
            time_high,
            time_mid,
            time_low_and_version,
            clk_seq_hi_res,
            clk_seq_low,
            node,
        )
    )


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


# Pydantic serializable UTC datetime type
UTCDateTime = Annotated[
    datetime,
    PlainSerializer(lambda dt: dt.isoformat(), return_type=str, when_used="json"),
]
