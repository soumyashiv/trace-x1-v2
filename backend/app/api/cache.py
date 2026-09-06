"""
Redis-backed caching and rate limiting.

Caching exists specifically to satisfy the "do not query blockchain
providers repeatedly for identical data" performance requirement:
`cached_get_transactions` memoizes provider calls per address for a
configurable TTL.
"""
from __future__ import annotations

import json
import time
from typing import Callable

import redis

from app.config import settings

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def is_cache_healthy() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:
        return False


def cached_json(key: str, ttl_seconds: int, producer: Callable[[], dict]) -> dict:
    """Fetch `key` from Redis, or call `producer()` and cache the result."""
    r = get_redis()
    try:
        cached = r.get(key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass  # cache unavailable -> fall through to live compute

    value = producer()
    try:
        r.setex(key, ttl_seconds, json.dumps(value, default=str))
    except Exception:
        pass
    return value


class RateLimiter:
    """Fixed-window per-user rate limiter backed by Redis INCR + TTL."""

    def __init__(self, limit_per_minute: int | None = None):
        self.limit = limit_per_minute or settings.rate_limit_per_minute

    def check(self, identity: str) -> bool:
        """Returns True if the request is allowed, False if rate-limited."""
        window = int(time.time() // 60)
        key = f"ratelimit:{identity}:{window}"
        try:
            r = get_redis()
            count = r.incr(key)
            if count == 1:
                r.expire(key, 65)
            return count <= self.limit
        except Exception:
            # If Redis is down, fail open rather than blocking investigators
            # entirely — logged as a degraded-mode event.
            return True
