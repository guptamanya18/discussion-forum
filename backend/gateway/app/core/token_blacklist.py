"""
This file keeps track of logged-out users so their old tokens can't be used again.

Token blacklist using Redis.

On logout, the token is added to Redis with a TTL equal to its remaining
lifetime. On every incoming request, the gateway checks if the token has
been blacklisted before forwarding.
"""

import logging
from datetime import datetime, timezone

from jose import jwt, JWTError

from app.core.config import settings
from app.core.cache import get_redis

logger = logging.getLogger(__name__)


# helps seperate from cache keys, rate limiting keys
BLACKLIST_PREFIX = "bl:"


def _decode_token(token: str) -> dict | None:

    # return payload dict
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


async def blacklist_token(token: str) -> bool:
    """Add a token to the blacklist. Returns True on success."""
    payload = _decode_token(token)
    if not payload:
        return False

    exp = payload.get("exp")
    if not exp:
        return False


    # calculate how much time token is still valid
    remaining = int(exp - datetime.now(timezone.utc).timestamp())
    if remaining <= 0:
        return True  # already expired, nothing to blacklist

    r = await get_redis()
    if r is None:
        logger.warning("Redis unavailable — cannot blacklist token")
        return False


   # store in redis  here 1 is just a marker
    await r.setex(BLACKLIST_PREFIX + token, remaining, "1")
    logger.info("Token blacklisted (TTL=%ds)", remaining)
    return True


async def is_token_blacklisted(authorization: str | None) -> bool:
    """Check if the Bearer token in the Authorization header is blacklisted on every request."""
    token = _extract_bearer_token(authorization)
    if not token:
        return False

    r = await get_redis()
    if r is None:
        return False  # fail open if Redis is down

    result = await r.exists(BLACKLIST_PREFIX + token)
    return result > 0
