"""
This file limits how many requests a user can make so the server doesn't crash.

Redis-backed sliding-window rate limiter for the API Gateway.

• Uses Redis sorted sets with timestamps for a true sliding window.
• Key = "rl:{client_id}:{bucket}"  where client_id is user_id (if
  authenticated) or client IP (anonymous).
• Buckets partition endpoints so auth routes get stricter limits
  (brute-force protection) while normal reads are more generous.
• Returns standard rate-limit headers (RateLimit-Limit, RateLimit-
  Remaining, Retry-After) so clients can self-throttle.
"""

import time
import logging
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# we keep a global redis connection which is shared across all requests

# lazy initialization as initially none -- created only when first request comes
_redis: Redis | None = None


async def _get_redis() -> Redis | None:
    global _redis
    if _redis is None:
        try:
            # if not connected create connection
            _redis = Redis.from_url(settings.redis_url, decode_responses=True)
            await _redis.ping()  # check if redis is alive

            # if redis fails -- dont block users allow all requests
        except Exception as exc:
            logger.warning("Rate-limiter: Redis unavailable (%s) – allowing request", exc)
            _redis = None
    return _redis


# ── Bucket classification ─────────────────────────────────────────

# bucket → (max_requests, window_seconds)
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "auth":    (20, 60),     # 20 req/min  (login, register, reset)
    "write":   (30, 60),     # 30 req/min  (POST/PUT/PATCH/DELETE)
    "read":    (100, 60),    # 100 req/min (GET)
    "default": (60, 60),     # 60 req/min  (fallback)
}

# Paths that are never rate-limited (health probes, docs)
EXEMPT_PATHS = ("/health", "/docs", "/openapi.json", "/redoc", "/")


def _classify(path: str, method: str) -> str:
    # decides which bucket path belongs to
    if path.startswith("/auth"):
        return "auth"
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return "write"
    if method == "GET":
        return "read"
    return "default"


def _client_id(request) -> str:
    """
    identify who is making the request 
    priority is logged in user 
    else ip address
    """
    auth = request.headers.get("authorization", "")

    # use token hash as identifier

    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
        # Use a hash of the token so the key stays compact
        return f"tok:{hash(token) & 0xFFFFFFFF:08x}"
    # X-Forwarded-For when behind a reverse proxy, else direct IP
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    
    # fallback -- use ip address so non logged in users are also limited
    return f"ip:{request.client.host}"


# ── Core sliding-window check ─────────────────────────────────────

async def check_rate_limit(request) -> dict | None:
    """
    Check whether the request is within its rate limit.

    Returns None if the request is allowed.
    Returns a dict with status_code, body, and headers if it should be
    rejected (HTTP 429).
    """
    path: str = request.url.path

    # Exempt paths
    if path in EXEMPT_PATHS:
        return None

    r = await _get_redis()
    if r is None:
        # Redis down → fail open (allow the request)
        return None
     
     # get bucket + limits
    bucket = _classify(path, request.method)
    max_requests, window = RATE_LIMITS[bucket]

    # identify client
    client = _client_id(request)
    key = f"rl:{client}:{bucket}"
    
    # define time window
    now = time.time()
    window_start = now - window

    # pipeline = batch multiple redis operations -> faster + atomic execution
    pipe = r.pipeline()
    try:
        # Remove entries older than the window means keep onlyu 60 seconds data
        pipe.zremrangebyscore(key, 0, window_start)

        # Add current request
        pipe.zadd(key, {f"{now}": now})

        # Count entries in the window
        pipe.zcard(key)

        # Auto-expire the key so Redis doesn't leak memory
        pipe.expire(key, window + 1)

        results = await pipe.execute()
    except Exception as exc:
        logger.warning("Rate-limiter: Redis pipeline error (%s) – allowing request", exc)
        return None

    request_count = results[2]
    remaining = max(0, max_requests - request_count)

    # Attach headers to every response (gateway adds them in main.py)
    # these headers help frontend to know limit, remaining requests , when request happens
    request.state.rate_limit_headers = {
        "X-RateLimit-Limit": str(max_requests),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(int(now + window)),
    }
    
    # block if limit exceeded
    if request_count > max_requests:
        retry_after = int(window - (now - window_start))
        return {
            "status_code": 429,
            "body": f'{{"detail":"Rate limit exceeded. Try again in {retry_after}s."}}',
            "headers": {
                **request.state.rate_limit_headers,
                "Retry-After": str(retry_after),
            },
        }

    return None
