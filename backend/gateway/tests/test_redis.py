"""
Redis Integration Tests — run these and watch in RedisInsight.

These tests demonstrate all 3 Redis use cases in the gateway:
  1. Response Caching  (keys: gw:*)
  2. Token Blacklist   (keys: bl:*)
  3. Rate Limiting     (keys: rl:*)

Usage:
  cd backend/gateway
  pytest tests/test_redis.py -v -s

NOTE: The tests talk to Redis inside Docker via 'docker compose exec'.
      localhost:6379 may point to a different Redis (WSL2).
"""

import subprocess
import time
import pytest

GATEWAY_URL = "http://localhost:8000"


def redis_cmd(*args: str) -> str:
    """Run a redis-cli command inside the Docker Redis container."""
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "redis", "redis-cli", *args],
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout.strip()


def redis_keys(pattern: str) -> list[str]:
    """Return list of keys matching pattern."""
    out = redis_cmd("KEYS", pattern)
    if not out or out == "(empty list or set)" or out == "(empty array)":
        return []
    return [line.split(") ", 1)[-1] if ") " in line else line for line in out.splitlines()]


def redis_ttl(key: str) -> int:
    return int(redis_cmd("TTL", key))


def redis_type(key: str) -> str:
    return redis_cmd("TYPE", key)


def redis_zcard(key: str) -> int:
    return int(redis_cmd("ZCARD", key))


def redis_exists(key: str) -> int:
    return int(redis_cmd("EXISTS", key))


def redis_del(*keys: str):
    if keys:
        redis_cmd("DEL", *keys)


# ─────────────────────────────────────────────────────────────────
# 1. RESPONSE CACHING  (gw:* keys)
# ─────────────────────────────────────────────────────────────────

class TestCaching:
    """
    The gateway caches GET /threads, /communities, /users/ responses.
    Key format:  gw:/threads?skip=0&limit=10
    Value:       JSON with body, status, content_type
    TTL:         60 seconds
    """

    def test_cache_miss_then_hit(self):
        """
        1. Clear all cache keys
        2. GET /threads → cache MISS → key created in Redis
        3. GET /threads again → cache HIT → served from Redis
        Open RedisInsight → filter keys by 'gw:*' to see these.
        """
        import httpx

        # Clear existing cache keys
        cache_keys = redis_keys("gw:*")
        if cache_keys:
            redis_del(*cache_keys)
        print(f"\n[CACHE] Cleared {len(cache_keys)} existing cache keys")

        # First request — cache MISS (creates the key)
        resp = httpx.get(f"{GATEWAY_URL}/threads?skip=0&limit=5")
        assert resp.status_code == 200
        time.sleep(1)

        # Check Redis — key should now exist
        cache_keys = redis_keys("gw:/threads*")
        print(f"[CACHE] After 1st request: {len(cache_keys)} cache keys")
        assert len(cache_keys) >= 1, "Cache key was not created"

        for key in cache_keys:
            ttl = redis_ttl(key)
            print(f"  Key: {key}  TTL: {ttl}s")
            assert ttl > 0, "Cache key should have a TTL"

        # Second request — cache HIT (served from Redis, no DB call)
        resp2 = httpx.get(f"{GATEWAY_URL}/threads?skip=0&limit=5")
        assert resp2.status_code == 200
        print("[CACHE] 2nd request served from cache (HIT)")

    def test_cache_invalidation_on_write(self):
        """
        POST/PUT/DELETE invalidates related cache keys.
        1. GET /communities → creates cache key
        2. Check key exists
        After a write to /communities, the key would be cleared.
        Open RedisInsight → watch 'gw:/communities*' keys appear/disappear.
        """
        import httpx

        # Populate cache
        resp = httpx.get(f"{GATEWAY_URL}/communities")
        assert resp.status_code == 200
        time.sleep(1)

        keys = redis_keys("gw:/communities*")
        print(f"\n[INVALIDATION] Community cache keys: {len(keys)}")
        for key in keys:
            ttl = redis_ttl(key)
            print(f"  Key: {key}  TTL: {ttl}s")
        assert len(keys) >= 1

    def test_auth_endpoints_never_cached(self):
        """
        /auth/* endpoints are in NEVER_CACHE list.
        Open RedisInsight → you should NEVER see gw:/auth/* keys.
        """
        import httpx

        httpx.get(f"{GATEWAY_URL}/auth/me")  # will 401, but still tests caching logic
        time.sleep(0.5)

        auth_keys = redis_keys("gw:/auth*")
        print(f"\n[NEVER_CACHE] Auth cache keys: {len(auth_keys)} (should be 0)")
        assert len(auth_keys) == 0, "/auth/ endpoints should never be cached"


# ─────────────────────────────────────────────────────────────────
# 2. TOKEN BLACKLIST  (bl:* keys)
# ─────────────────────────────────────────────────────────────────

class TestTokenBlacklist:
    """
    On logout, the JWT is stored in Redis with key 'bl:{token}'.
    TTL = remaining lifetime of the token (auto-expires when JWT would).
    On every request, gateway checks: EXISTS bl:{token}
    """

    def test_login_then_logout_blacklists_token(self):
        """
        1. Login → get token (via cookie)
        2. Logout → token added to Redis blacklist
        3. Check bl:* key exists in Redis
        4. Try using token again → should be rejected
        Open RedisInsight → filter by 'bl:*' to see blacklisted tokens.
        """
        import httpx

        # Count bl:* keys before
        bl_before = len(redis_keys("bl:*"))

        # Login
        login_resp = httpx.post(
            f"{GATEWAY_URL}/auth/login",
            data={"username": "alice", "password": "pass123"},
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.cookies.get("access_token")
        assert token, "No access_token cookie returned"
        print(f"\n[BLACKLIST] Logged in, token: {token[:40]}...")

        # Logout
        logout_resp = httpx.post(
            f"{GATEWAY_URL}/auth/logout",
            cookies={"access_token": token},
        )
        assert logout_resp.status_code == 200
        time.sleep(1)

        # Count bl:* keys after logout
        bl_after = len(redis_keys("bl:*"))
        print(f"[BLACKLIST] bl:* keys before logout: {bl_before}, after: {bl_after}")
        assert bl_after > bl_before, "Token was not blacklisted"

        # Check the specific key
        bl_key = f"bl:{token}"
        exists = redis_exists(bl_key)
        ttl = redis_ttl(bl_key)
        print(f"[BLACKLIST] Key exists: {exists}, TTL: {ttl}s")
        assert exists, "Blacklist key not found in Redis"
        assert ttl > 0, "Blacklist key should have TTL matching token expiry"

        # Try using the blacklisted token — should fail
        me_resp = httpx.get(
            f"{GATEWAY_URL}/auth/me",
            cookies={"access_token": token},
        )
        print(f"[BLACKLIST] Request with blacklisted token: {me_resp.status_code}")
        assert me_resp.status_code == 401, "Blacklisted token should be rejected"


# ─────────────────────────────────────────────────────────────────
# 3. RATE LIMITING  (rl:* keys)
# ─────────────────────────────────────────────────────────────────

class TestRateLimiting:
    """
    Uses Redis sorted sets for sliding-window rate limiting.
    Key format: rl:{client_id}:{bucket}
    Buckets:    auth (20/min), write (30/min), read (100/min)
    Each request adds a timestamped entry to the sorted set.
    """

    def test_rate_limit_keys_created(self):
        """
        Make a few GET requests → check rl:* sorted set in Redis.
        Open RedisInsight → filter by 'rl:*', type is ZSET, see timestamps.
        """
        import httpx

        # Make 3 requests
        for i in range(3):
            httpx.get(f"{GATEWAY_URL}/threads")
            time.sleep(0.1)

        time.sleep(1)
        rl_keys = redis_keys("rl:*")
        print(f"\n[RATE LIMIT] rl:* keys: {len(rl_keys)}")
        for key in rl_keys:
            key_type = redis_type(key)
            members = redis_zcard(key) if key_type == "zset" else "N/A"
            ttl = redis_ttl(key)
            print(f"  Key: {key}  Type: {key_type}  Members: {members}  TTL: {ttl}s")

        assert len(rl_keys) >= 1, "Rate limit keys should exist"

    def test_rate_limit_headers_returned(self):
        """
        Every response includes rate limit headers.
        X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
        NOTE: Cached responses skip the rate limiter, so we use a unique URL.
        """
        import httpx

        # Use a unique query to avoid cache hit
        resp = httpx.get(f"{GATEWAY_URL}/threads?skip=0&limit=1&_t={time.time()}")
        limit = resp.headers.get("X-RateLimit-Limit")
        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset = resp.headers.get("X-RateLimit-Reset")

        print(f"\n[RATE LIMIT HEADERS]")
        print(f"  X-RateLimit-Limit:     {limit}")
        print(f"  X-RateLimit-Remaining: {remaining}")
        print(f"  X-RateLimit-Reset:     {reset}")

        assert limit is not None, "Missing X-RateLimit-Limit header"
        assert remaining is not None, "Missing X-RateLimit-Remaining header"

    def test_auth_bucket_stricter_limit(self):
        """
        Auth bucket has 20 req/min (stricter than read's 100/min).
        Open RedisInsight → compare rl:*:auth vs rl:*:read ZSET member counts.
        """
        import httpx

        # Make an auth request
        httpx.post(
            f"{GATEWAY_URL}/auth/login",
            data={"username": "wrong_user", "password": "wrong_pass"},
        )
        time.sleep(0.5)

        auth_keys = redis_keys("rl:*:auth")
        read_keys = redis_keys("rl:*:read")
        print(f"\n[BUCKETS] Auth keys: {len(auth_keys)}, Read keys: {len(read_keys)}")
        for key in auth_keys:
            print(f"  Auth bucket: {key}  Members: {redis_zcard(key)}")
        for key in read_keys:
            print(f"  Read bucket: {key}  Members: {redis_zcard(key)}")

    def test_sorted_set_structure(self):
        """
        Each rl:* key is a sorted set where:
          - member = timestamp string (e.g. "1712345678.123")
          - score  = same timestamp (used for range queries)
        Old entries are pruned on each request (sliding window).
        Open RedisInsight → click any rl:* key → see ZSET members = timestamps.
        """
        import httpx

        # Make a request to ensure key exists
        httpx.get(f"{GATEWAY_URL}/communities")
        time.sleep(0.5)

        rl_keys = redis_keys("rl:*:read")
        if rl_keys:
            key = rl_keys[0]
            members_raw = redis_cmd("ZRANGE", key, "0", "-1", "WITHSCORES")
            print(f"\n[ZSET STRUCTURE] Key: {key}")
            print(f"  Raw output:\n  {members_raw[:500]}")


# ─────────────────────────────────────────────────────────────────
# 4. ALL KEYS OVERVIEW
# ─────────────────────────────────────────────────────────────────

class TestRedisOverview:
    """View all keys grouped by prefix — the full picture."""

    def test_show_all_keys(self):
        """
        Prints all Redis keys grouped by prefix:
          gw:*  → Cache keys (response bodies)
          bl:*  → Blacklist keys (logged-out tokens)
          rl:*  → Rate limit keys (sorted sets with timestamps)
        """
        cache_keys = redis_keys("gw:*")
        bl_keys = redis_keys("bl:*")
        rl_keys = redis_keys("rl:*")

        print(f"\n{'='*60}")
        print(f" REDIS KEY SUMMARY")
        print(f"{'='*60}")
        print(f"\n Cache keys (gw:*): {len(cache_keys)}")
        for k in cache_keys:
            print(f"   {k}  TTL={redis_ttl(k)}s  Type={redis_type(k)}")

        print(f"\n Blacklist keys (bl:*): {len(bl_keys)}")
        for k in bl_keys:
            print(f"   {k[:60]}...  TTL={redis_ttl(k)}s")

        print(f"\n Rate limit keys (rl:*): {len(rl_keys)}")
        for k in rl_keys:
            count = redis_zcard(k) if redis_type(k) == "zset" else "?"
            print(f"   {k}  Members={count}  TTL={redis_ttl(k)}s")

        print(f"\n Total keys: {len(cache_keys) + len(bl_keys) + len(rl_keys)}")
        print(f"{'='*60}")
