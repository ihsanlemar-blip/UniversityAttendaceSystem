"""Deterministic Redis-backed rate limiting with in-memory test fallback.

Enforces:
- Section 11/12 rate limiting requirements across auth, devices, check-in, and imports.
- Returns HTTP 429 with Retry-After header.
- Safe enumeration prevention (consistent rate limiting without leaking account existence).
- Resilient fallback to thread-safe in-memory sliding window when Redis is unavailable.
"""

import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request

from backend.app.core.config import get_settings
from backend.app.core.exceptions import RateLimitExceededException
from backend.app.core.logging import get_logger
from backend.app.core.redis import get_redis
from backend.app.security.resolver import ClientNetworkResolver

logger = get_logger(__name__)

# Fallback in-memory tracking: {key: [monotonic_timestamp, ...]}
_in_memory_buckets: dict[str, list[float]] = defaultdict(list)


class RateLimiter:
    """Core rate limiting coordinator supporting Redis and local memory."""

    @staticmethod
    async def check_rate_limit(
        key: str,
        max_requests: int,
        window_seconds: int,
        force: bool = False,
    ) -> None:
        """Evaluate rate limit for a specific bucket key.

        Raises:
            RateLimitExceededException: If maximum allowed requests exceeded in window.
        """
        if not force:
            settings = get_settings()
            if not getattr(settings, "RATE_LIMITING_ENABLED", True):
                return

        now = time.monotonic()

        # 1. Try Redis first
        try:
            redis_client = await get_redis()
            redis_key = f"ratelimit:{key}"

            async with redis_client.pipeline(transaction=True) as pipe:
                pipe.incr(redis_key)
                pipe.ttl(redis_key)
                results = await pipe.execute()

            count = int(results[0])
            ttl = int(results[1])

            # If key was just created, set the TTL
            if count == 1 or ttl < 0:
                await redis_client.expire(redis_key, window_seconds)
                ttl = window_seconds

            if count > max_requests:
                retry_after = max(ttl, 1)
                logger.warning(
                    f"Rate limit exceeded on key '{key}': {count}/{max_requests} "
                    f"(retry after {retry_after}s)"
                )
                raise RateLimitExceededException(
                    retry_after=retry_after,
                    message=f"Rate limit exceeded. Please try again in {retry_after} seconds.",
                    details={"limit": max_requests, "window_seconds": window_seconds},
                )
            return

        except RateLimitExceededException:
            raise
        except Exception as exc:
            logger.debug(f"Redis rate limiter unavailable ({exc}); using in-memory bucket.")

        # 2. In-memory fallback
        window_start = now - window_seconds
        timestamps = _in_memory_buckets[key]
        # Prune old timestamps
        _in_memory_buckets[key] = [t for t in timestamps if t > window_start]
        current_bucket = _in_memory_buckets[key]

        if len(current_bucket) >= max_requests:
            oldest_entry = current_bucket[0]
            retry_after = max(int(window_seconds - (now - oldest_entry)) + 1, 1)
            logger.warning(
                f"In-memory rate limit exceeded on key '{key}': "
                f"{len(current_bucket)}/{max_requests} (retry after {retry_after}s)"
            )
            raise RateLimitExceededException(
                retry_after=retry_after,
                message=f"Rate limit exceeded. Please try again in {retry_after} seconds.",
                details={"limit": max_requests, "window_seconds": window_seconds},
            )

        current_bucket.append(now)

    @classmethod
    def reset_in_memory(cls) -> None:
        """Clear all in-memory rate limit state (useful in test teardown)."""
        _in_memory_buckets.clear()


def rate_limit(
    action: str,
    max_requests: int,
    window_seconds: int = 60,
    key_func: Callable[[Request], str] | None = None,
) -> Callable:
    """FastAPI dependency factory enforcing rate limits on endpoints.

    Args:
        action: Identifier for the endpoint or operation being protected.
        max_requests: Number of permitted requests within the window.
        window_seconds: Window duration in seconds (default: 60).
        key_func: Optional custom key generator callable receiving Request.
    """

    async def _rate_limit_dependency(request: Request) -> None:
        if key_func:
            identifier = key_func(request)
        else:
            identifier = ClientNetworkResolver.resolve_client_ip(request)

        key = f"{action}:{identifier}"
        await RateLimiter.check_rate_limit(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

    return _rate_limit_dependency
