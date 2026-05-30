"""
Redis client factory + a small sliding-window rate limiter.

The RateLimiter is used by outreach tools to cap how many messages a single
rental search can send per day (anti-spam, anti-blacklist). It exposes exactly
two operations the tools need: read the current count, and increment it.

Karpathy rule: small and explicit. INCR + EXPIRE is atomic enough for our
per-search daily caps; we do not need a Lua script here.
"""
from __future__ import annotations

from redis.asyncio import Redis, from_url

from ..config import Settings

_redis: Redis | None = None


async def init_redis(settings: Settings) -> Redis:
    """Create the process-wide Redis client. Idempotent."""
    global _redis
    if _redis is None:
        _redis = from_url(settings.redis_url, decode_responses=True)
    return _redis


async def get_redis_client() -> Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized — call init_redis() at startup.")
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


class RateLimiter:
    """
    Per-key daily counter backed by Redis.

    Usage:
        count = await limiter.get_count("email_outreach:<search_id>")
        if count >= MAX:
            ...refuse...
        await limiter.increment("email_outreach:<search_id>", ttl_seconds=86400)
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get_count(self, key: str) -> int:
        value = await self._redis.get(key)
        return int(value) if value is not None else 0

    async def increment(self, key: str, ttl_seconds: int) -> int:
        """Increment the counter; set the TTL on first write so the window expires."""
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, ttl_seconds)
        return int(count)
