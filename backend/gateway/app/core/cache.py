"""
Simple Redis cache for the API Gateway.

How it works:
─────────────
1. GET requests   → check Redis first. If cached, return instantly (skip microservice call)
2. Cache miss     → forward to microservice, store response in Redis with a TTL
3. POST/PUT/DELETE → forward to microservice, then clear related cache keys

Cache keys are based on the URL path + query string.
Only public/read endpoints are cached (threads, communities).
Auth-dependent endpoints (notifications, /auth/me) are NEVER cached.
"""

import json
import logging
from redis.asyncio import from_url as redis_from_url

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis connection (lazy init)
_redis = None

# TTL in seconds (how long cached data lives)
CACHE_TTL = 60

# Only cache GET requests matching these prefixes
CACHEABLE_PREFIXES = [
    "/threads",
    "/communities",
    "/users/",
]

# NEVER cache these (auth-dependent or real-time)
NEVER_CACHE = [
    "/auth/",
    "/notifications",
    "/health",
    "/uploads/",
    "/communities/my",
    "/users/me/",
    "/users/mod/",
    "/users/admin/",
]

# When a write hits these prefixes, clear cache keys matching the pattern
# e.g. POST /comments with thread_id → clear /threads* cache
INVALIDATION_MAP = {
    "/threads":     ["/threads"],
    "/comments":    ["/threads", "/comments"],
    "/communities": ["/communities"],
    "/users":       ["/users"],
}


async def get_redis():

    # create redis connection
    global _redis
    if _redis is None:
        try:
            _redis = redis_from_url(settings.redis_url, decode_responses=True)
            await _redis.ping()
            logger.info("Redis connected at %s", settings.redis_url)

        # if redis is down we disable caching (fail-safe)
        except Exception as e:
            logger.warning("Redis unavailable, caching disabled: %s", e)
            _redis = None
    return _redis


# decide whether a request should be cached or not
def _should_cache(path: str) -> bool:
    """Return True if this GET path should be cached."""
    for prefix in NEVER_CACHE:
        if path.startswith(prefix):
            return False
    for prefix in CACHEABLE_PREFIXES:
        if path.startswith(prefix):
            return True
    return False

# create a unique cache key that is to be stored
def _cache_key(path: str, query: str) -> str:
    """Build a Redis key from path + query string."""
    key = f"gw:{path}"
    if query:
        key += f"?{query}"
    return key


async def get_cached(path: str, query: str) -> tuple[bytes, int, str] | None:
    """
    Try to get a cached response.
    Returns (body, status_code, content_type) or None.
    """
    r = await get_redis()
    if r is None:
        return None
    if not _should_cache(path):
        return None

    key = _cache_key(path, query)
    try:
        data = await r.get(key)
        if data:
            cached = json.loads(data)
            logger.info("Cache HIT: %s", key)
            return cached["body"].encode(), cached["status"], cached["content_type"]
    except Exception:
        pass
    return None


async def set_cached(path: str, query: str, body: bytes, status: int, content_type: str):
    """Store a response in Redis."""
    r = await get_redis()
    if r is None:
        return
    if not _should_cache(path):
        return
    if status >= 400:
        return  # don't cache errors

    key = _cache_key(path, query)
    try:
        data = json.dumps({
            "body": body.decode(),
            "status": status,
            "content_type": content_type,
        })
        await r.setex(key, CACHE_TTL, data)
        logger.info("Cache SET: %s (TTL=%ds)", key, CACHE_TTL)
    except Exception:
        pass


async def invalidate_cache(path: str):
    """Clear cached keys related to this write path."""
    r = await get_redis()
    if r is None:
        return

    for prefix, patterns in INVALIDATION_MAP.items():
        if path.startswith(prefix):
            for pattern in patterns:
                try:
                    keys = []
                    async for key in r.scan_iter(f"gw:{pattern}*"):
                        keys.append(key)
                    if keys:
                        await r.delete(*keys)
                        logger.info("Cache INVALIDATED: %d keys matching %s*", len(keys), pattern)
                except Exception:
                    pass
            break
