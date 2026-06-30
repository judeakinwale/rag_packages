from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from rag_packages.shared.redis.client import (
    REFRESH_LOCK_SCRIPT,
    RELEASE_LOCK_SCRIPT,
    RedisClient,
)


def make_client(redis):
    client = RedisClient.__new__(RedisClient)
    client.client = redis
    return client


@pytest.mark.asyncio
async def test_set_supports_nx_option():
    redis = SimpleNamespace(set=AsyncMock(return_value=True))
    client = make_client(redis)

    result = await client.set("cache:key", "value", ex=30, nx=True)

    assert result is True
    redis.set.assert_awaited_once_with("cache:key", "value", ex=30, nx=True)


@pytest.mark.asyncio
async def test_acquire_lock_returns_token_when_lock_is_acquired():
    redis = SimpleNamespace(set=AsyncMock(return_value=True))
    client = make_client(redis)

    result = await client.acquire_lock("locks:sharepoint", 300, token="owner-token")

    assert result == "owner-token"
    redis.set.assert_awaited_once_with(
        "locks:sharepoint",
        "owner-token",
        ex=300,
        nx=True,
    )


@pytest.mark.asyncio
async def test_acquire_lock_returns_none_when_lock_exists():
    redis = SimpleNamespace(set=AsyncMock(return_value=False))
    client = make_client(redis)

    result = await client.acquire_lock("locks:sharepoint", 300, token="owner-token")

    assert result is None


@pytest.mark.asyncio
async def test_release_lock_uses_token_checked_script():
    redis = SimpleNamespace(eval=AsyncMock(return_value=1))
    client = make_client(redis)

    result = await client.release_lock("locks:sharepoint", "owner-token")

    assert result is True
    redis.eval.assert_awaited_once_with(
        RELEASE_LOCK_SCRIPT,
        1,
        "locks:sharepoint",
        "owner-token",
    )


@pytest.mark.asyncio
async def test_refresh_lock_uses_token_checked_script():
    redis = SimpleNamespace(eval=AsyncMock(return_value=1))
    client = make_client(redis)

    result = await client.refresh_lock("locks:sharepoint", "owner-token", 300)

    assert result is True
    redis.eval.assert_awaited_once_with(
        REFRESH_LOCK_SCRIPT,
        1,
        "locks:sharepoint",
        "owner-token",
        300,
    )
