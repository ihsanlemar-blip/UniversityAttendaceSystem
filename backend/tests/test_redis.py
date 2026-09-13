"""Unit tests for async Redis client and connectivity checks."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.app.core import redis as redis_module


@pytest.mark.asyncio
async def test_redis_init_and_close() -> None:
    """Verify init_redis initializes client and close_redis closes it."""
    # Ensure fresh state
    redis_module._redis_client = None

    mock_client = AsyncMock()
    with patch("backend.app.core.redis.aioredis.from_url", return_value=mock_client):
        client = await redis_module.init_redis()
        assert client == mock_client
        assert redis_module._redis_client == mock_client

        # get_redis returns existing client
        same_client = await redis_module.get_redis()
        assert same_client == mock_client

        # close_redis closes and resets
        await redis_module.close_redis()
        mock_client.close.assert_awaited_once()
        assert redis_module._redis_client is None


@pytest.mark.asyncio
async def test_check_redis_connectivity_success() -> None:
    """Verify check_redis_connectivity returns True when PING succeeds."""
    mock_client = AsyncMock()
    mock_client.ping.return_value = True

    with patch("backend.app.core.redis.get_redis", return_value=mock_client):
        result = await redis_module.check_redis_connectivity()
        assert result is True
        mock_client.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_redis_connectivity_failure() -> None:
    """Verify check_redis_connectivity returns False when connection error occurs."""
    mock_client = AsyncMock()
    mock_client.ping.side_effect = ConnectionError("Cannot reach Redis")

    with patch("backend.app.core.redis.get_redis", return_value=mock_client):
        result = await redis_module.check_redis_connectivity()
        assert result is False
