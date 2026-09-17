"""Asynchronous Redis client and connection pool lifecycle management."""

import asyncio

import redis.asyncio as aioredis
from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: aioredis.Redis | None = None


async def init_redis() -> aioredis.Redis:
    """Initialize the asynchronous Redis client and connection pool."""
    global _redis_client
    settings = get_settings()
    logger.info(f"Connecting to Redis at {settings.REDIS_URL}...")
    _redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    return _redis_client


async def get_redis() -> aioredis.Redis:
    """Return the active Redis client or initialize if not yet created."""
    global _redis_client
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _redis_client is not None:
        try:
            pool = _redis_client.connection_pool
            pool_loop = getattr(pool, "_loop", None)
            if pool_loop is not None and (
                pool_loop.is_closed() or (current_loop and pool_loop != current_loop)
            ):
                _redis_client = None
        except Exception:
            _redis_client = None

    if _redis_client is None:
        return await init_redis()
    return _redis_client


async def close_redis() -> None:
    """Close the active Redis connection pool gracefully."""
    global _redis_client
    if _redis_client is not None:
        logger.info("Closing Redis connection pool...")
        await _redis_client.close()
        _redis_client = None


async def check_redis_connectivity() -> bool:
    """Execute a PING command to verify Redis service availability."""
    try:
        client = await get_redis()
        response = await client.ping()
        return bool(response)
    except Exception as exc:
        logger.warning(f"Redis readiness check failed: {exc}")
        return False
