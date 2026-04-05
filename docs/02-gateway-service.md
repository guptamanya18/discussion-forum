# 02 — API Gateway Service (Port 8000)

## What Does the Gateway Do?

**Simple analogy:** The gateway is like a receptionist at a hospital. You walk in and say "I need an eye doctor." The receptionist doesn't treat you — they just point you to the right department. Similarly, the gateway receives all API requests and routes them to the correct microservice.

**In interview terms:** The API Gateway is a reverse proxy that acts as the single entry point for all client requests. It handles cross-cutting concerns like routing, caching, rate limiting, authentication (cookie/token management), and token blacklisting — none of which the individual microservices need to worry about.

---

## Key Responsibilities

1. **Request Routing** — Looks at the URL path and forwards to the correct microservice
2. **httpOnly Cookie Auth** — Sets a secure cookie on login, reads it on every request, injects the Authorization header before forwarding
3. **Redis Caching** — Caches GET responses, auto-invalidates on write operations
4. **Rate Limiting** — Sliding-window algorithm per client using Redis sorted sets
5. **Token Blacklisting** — On logout, the token is added to Redis so it can't be reused
6. **CORS** — Configured to allow the React frontend at `http://localhost:3000`

---

## How Routing Works

The gateway matches the URL path against a prefix table. **Order matters** — longer prefixes are checked first:

```
URL Path                    → Target Service
──────────────────────────────────────────────
/uploads/*                  → User Service (:8002)
/notifications/*            → Notification Service (:8007)
/communities/*              → Community Service (:8006)
/reports/*                  → Thread Service (:8003)
/threads/*                  → Thread Service (:8003)
/threads/{id}/comments/*    → Comment Service (:8005)   ← special delegation
/comments/*                 → Comment Service (:8005)
/auth/*                     → User Service (:8002)
/users/*                    → User Service (:8002)
```

**Special case:** `/threads/5/comments` goes to the Comment Service, not the Thread Service. The gateway detects this by checking if the 3rd URL segment starts with "comments".

---

## httpOnly Cookie Authentication

**Why cookies instead of localStorage?**
- `localStorage` is accessible to any JavaScript on the page — if an attacker injects a script (XSS), they can steal the token
- `httpOnly` cookies **cannot be read by JavaScript at all** — the browser sends them automatically, but `document.cookie` won't show them

**Flow:**

```
1. LOGIN
   Client → POST /auth/login (username + password)
   Gateway → forwards to User Service
   User Service → returns { access_token: "eyJ...", token_type: "bearer" }
   Gateway → sets httpOnly cookie with the token
   Gateway → strips access_token from response body (so JS never sees it)
   Client receives → { token_type: "bearer" } + cookie is set by browser

2. EVERY REQUEST AFTER LOGIN
   Browser automatically sends the cookie
   Gateway reads token from cookie
   Gateway injects: Authorization: Bearer <token> into headers
   Gateway forwards request with the header to the target service
   Target service reads Authorization header (doesn't know about cookies)

3. LOGOUT
   Client → POST /auth/logout
   Gateway reads token from cookie
   Gateway blacklists the token in Redis (with TTL = remaining JWT lifetime)
   Gateway deletes the cookie from browser
```

**Cookie settings:**
| Property | Value | Why |
|----------|-------|-----|
| `httpOnly` | `true` | JS cannot read it |
| `samesite` | `lax` | CSRF protection |
| `secure` | `false` | Set `true` in production (HTTPS only) |
| `max_age` | 5400 (90 min) | Matches JWT expiry |
| `path` | `/` | Sent on all routes |

---

## Redis Caching

**How it works:**
- Every GET response is cached in Redis with a key like `gw:/threads/?search=python`
- Cache TTL is set per path (e.g., 30 seconds for threads)
- On any POST/PUT/PATCH/DELETE, the cache for that path prefix is invalidated
- Response headers include `X-Cache: HIT` or `X-Cache: MISS`

**Example:**
```
GET /threads/ → Cache MISS → forward to Thread Service → store in Redis → return
GET /threads/ → Cache HIT → return from Redis (no microservice call)
POST /threads/ → invalidate /threads/* cache
GET /threads/ → Cache MISS again (fresh data)
```

---

## Rate Limiting

**Algorithm:** Sliding window using Redis Sorted Sets

**How it works (simplified):**
1. Each client gets a key like `rl:ip:192.168.1.1:read`
2. Each request adds a timestamp to a sorted set
3. Timestamps older than the window (60s) are removed
4. If the count exceeds the limit → 429 Too Many Requests

**Buckets and limits:**

| Bucket | Limit | Window | Applies To |
|--------|-------|--------|------------|
| `auth` | 20 req | 60s | Login, register, password reset |
| `write` | 30 req | 60s | POST, PUT, PATCH, DELETE |
| `read` | 100 req | 60s | GET requests |

**Response headers on every request:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 97
X-RateLimit-Reset: 1712188800
```

**Exempt paths:** `/health`, `/docs`, `/openapi.json`, `/`

---

## Token Blacklisting

When a user logs out:
1. Their JWT token is added to Redis with key `bl:<token>`
2. The TTL is set to the remaining lifetime of the token
3. On every request, the gateway checks if the token exists in the blacklist
4. If yes → 401 Unauthorized

**Why?** JWTs are stateless — without blacklisting, a stolen token works until it expires (90 minutes). Blacklisting lets us invalidate it immediately on logout.

---

## File Structure

```
backend/gateway/
├── app/
│   ├── main.py              # Gateway routes, proxy logic, cookie handling
│   └── core/
│       ├── config.py         # Pydantic settings (service URLs, Redis URL, secret key)
│       ├── cache.py          # Redis GET caching + invalidation
│       ├── rate_limiter.py   # Sliding-window rate limiter
│       └── token_blacklist.py # JWT blacklist on logout
├── pyproject.toml            # Dependencies (fastapi, httpx, redis, python-jose)
└── logs/
    └── gateway.log           # Rotating log file (5MB, 3 backups)
```

---

## Key Dependencies

```
fastapi        — Web framework
httpx          — Async HTTP client (for proxying requests to microservices)
redis[asyncio] — Redis client (caching, rate limiting, blacklisting)
python-jose    — JWT decoding (for blacklist TTL calculation)
pydantic-settings — Environment variable management
uvicorn        — ASGI server
```

---

## Interview Q&A

**Q: Why not just let the frontend call each microservice directly?**
A: The gateway provides a single entry point so the frontend only needs to know one URL (port 8000). It also handles cross-cutting concerns (auth, caching, rate limiting) in one place instead of duplicating them in every service.

**Q: What happens if Redis goes down?**
A: The gateway "fails open" — all requests are allowed through (no caching, no rate limiting). This is a deliberate design choice: availability over strictness.

**Q: How does the gateway know which service to route to?**
A: It matches the URL path against a prefix table. The routing is deterministic — same path always goes to the same service. No service discovery is needed because Docker Compose gives each service a fixed hostname.
