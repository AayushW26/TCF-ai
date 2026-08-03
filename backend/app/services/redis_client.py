"""
Redis client — connection pool, conversation state management, and caching.

Uses Upstash Redis (TLS-enabled) via the standard `redis` library.
"""

import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Module-level connection pool
_pool: Optional[aioredis.Redis] = None


async def init_redis(redis_url: str) -> aioredis.Redis:
    """Initialise the async Redis connection pool. Called once at startup."""
    global _pool
    _pool = aioredis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        retry_on_timeout=True,
    )
    # Verify connectivity
    await _pool.ping()
    logger.info("Redis connection established")
    return _pool


def get_redis() -> aioredis.Redis:
    """Return the initialised Redis client."""
    if _pool is None:
        raise RuntimeError("Redis not initialised — call init_redis() first")
    return _pool


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None
        logger.info("Redis connection closed")


# ── Conversation State Management ────────────────────────────


async def get_conversation_state(phone: str) -> Optional[Dict[str, Any]]:
    """Get the current conversation state for a phone number."""
    key = f"conv:{phone}"
    data = await get_redis().get(key)
    if data:
        return json.loads(data)
    return None


async def set_conversation_state(
    phone: str,
    state: str,
    context: Optional[Dict[str, Any]] = None,
    ttl: int = 3600,
) -> None:
    """Set the conversation state for a phone number with TTL."""
    key = f"conv:{phone}"
    payload = {
        "state": state,
        "context": context or {},
    }
    await get_redis().setex(key, ttl, json.dumps(payload))


async def delete_conversation_state(phone: str) -> None:
    """Delete the conversation state for a phone number."""
    key = f"conv:{phone}"
    await get_redis().delete(key)


# ── General Caching ──────────────────────────────────────────


async def cache_get(key: str) -> Optional[str]:
    """Get a cached value by key."""
    return await get_redis().get(f"cache:{key}")


async def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    """Set a cached value with TTL."""
    await get_redis().setex(f"cache:{key}", ttl, value)


async def cache_delete(key: str) -> None:
    """Delete a cached value."""
    await get_redis().delete(f"cache:{key}")


async def cache_get_json(key: str) -> Optional[Dict[str, Any]]:
    """Get a cached JSON value."""
    data = await cache_get(key)
    if data:
        return json.loads(data)
    return None


async def cache_set_json(key: str, value: Dict[str, Any], ttl: int = 3600) -> None:
    """Cache a value as JSON."""
    await cache_set(key, json.dumps(value), ttl)
