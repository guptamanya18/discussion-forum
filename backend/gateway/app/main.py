"""
API Gateway – routes all incoming requests to the appropriate microservice.

Routing table
─────────────
/auth/*                  → user_service      (port 8002)
/users/*                 → user_service      (port 8002)
/threads/*               → thread_service    (port 8003)
/threads/{id}/comments   → comment_service   (port 8005)
/comments/*              → comment_service   (port 8005)

All headers (including Authorization) and query parameters are forwarded
transparently. The gateway itself performs no authentication.
"""

import json
import logging
import os
from logging.handlers import RotatingFileHandler
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

# ── Logging: console + rotating file ──
# print logs in console , store logs in a file, rotate file when size exceeds

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
_fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
_console = logging.StreamHandler()
_console.setFormatter(_fmt)
_file = RotatingFileHandler(os.path.join(LOG_DIR, "gateway.log"), maxBytes=5_000_000, backupCount=3)
_file.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_console, _file])

from app.core.config import settings
from app.core.cache import get_cached, set_cached, invalidate_cache
from app.core.token_blacklist import blacklist_token, is_token_blacklisted
from app.core.rate_limiter import check_rate_limit
from app.core.exceptions import register_exception_handlers


app = FastAPI(title="API Gateway")
register_exception_handlers(app)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    # Remove the full_path parameter from the catch-all proxy route
    for path_data in schema.get("paths", {}).values():
        for method_data in path_data.values():
            if isinstance(method_data, dict) and "parameters" in method_data:
                method_data["parameters"] = [
                    p for p in method_data["parameters"]
                    if p.get("name") != "full_path"
                ]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi

# Root route for friendly info
@app.get("/")
def root():
    return {
        "service": "gateway",
        "status": "ok",
        "message": "Welcome to the Discussion Forum API Gateway.",
        "docs": "/docs",
        "health": "/health",
        "routes": [
            "/auth/*",
            "/users/*",
            "/threads/*",
            "/threads/{id}/comments",
            "/comments/*",
            "/communities/*",
            "/notifications/*"
        ]
    }


# allows frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After"],
)


COOKIE_NAME = "access_token"
COOKIE_MAX_AGE = 90 * 60  # 90 minutes (matches JWT expiry)



def _extract_token_from_request(request: Request) -> str | None:
    """Extract JWT from cookie (primary) or Authorization header (fallback)."""
   
    # firstly it get token from cookie used by browser

    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    
    # fallback: check authorization headers also if its a bearer token

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1]
    return None


@app.post("/auth/logout", tags=["Auth"])
async def logout(request: Request):
    """Blacklist the current token so it can no longer be used."""
    token = _extract_token_from_request(request)
    if token:
        await blacklist_token(token)   # add token to blacklist
    response = Response(
        content=json.dumps({"message": "Logged out"}),
        media_type="application/json",
    )

    # delete cookie from browser
    response.delete_cookie(COOKIE_NAME, path="/", samesite="lax")
    return response


@app.get("/health")
def health():
    return {
        "service": "gateway",
        "status": "ok",
        "routes": {
            "auth":      settings.user_service_url,
            "user":      settings.user_service_url,
            "thread":    settings.thread_service_url,
            "comment":   settings.comment_service_url,
            "community": settings.community_service_url,
            "notification": settings.notification_service_url,
        },
        "cache": "redis @ " + settings.redis_url,
    }


# shows cached keys in redis, ttl 
@app.get("/cache-stats")
async def cache_stats():
    
    from app.core.cache import get_redis
    r = await get_redis()
    if r is None:
        return {"status": "Redis not available", "keys": []}
    keys = [key async for key in r.scan_iter("gw:*")]
    ttls = {}
    for key in keys:
        ttl = await r.ttl(key)
        ttls[key] = f"{ttl}s remaining"
    return {"status": "connected", "cached_keys": len(keys), "keys": ttls}


# ── route prefix → target base URL (order matters: longer prefixes first) ──
_ROUTES: list[tuple[str, str]] = [
    ("/uploads/", settings.user_service_url),
    ("/notifications/", settings.notification_service_url),
    ("/notifications", settings.notification_service_url),
    ("/communities/", settings.community_service_url),
    ("/communities", settings.community_service_url),
    ("/reports/", settings.thread_service_url),
    ("/reports", settings.thread_service_url),
    ("/threads/", settings.thread_service_url),
    ("/comments/", settings.comment_service_url),
    ("/comments", settings.comment_service_url),
    ("/auth/", settings.user_service_url),
    ("/auth", settings.user_service_url),
    ("/users/admin/users/", settings.user_service_url),
    ("/users/admin/users", settings.user_service_url),
    ("/users/", settings.user_service_url),
    ("/users", settings.user_service_url),
]

# Routes that start with /threads/ but belong to comment_service
_THREAD_DELEGATED: list[tuple[str, str]] = [
    ("/comments", settings.comment_service_url),
]

# tells tail is the service we have to go

def _resolve_target(path: str) -> str | None:
    """Return the base URL of the service that should handle this path."""
    # Special case: /threads/{id}/comments  →  comment_service
    parts = path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "threads":
        tail = "/" + "/".join(parts[2:])
        for prefix, url in _THREAD_DELEGATED:
            if tail.startswith(prefix):
                return url

    for prefix, url in _ROUTES:
        if path.startswith(prefix) or path == prefix.rstrip("/"):
            return url
    return None

# main function

@app.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    tags=["Proxy"],
    summary="Gateway proxy – forwards requests to microservices",
)
async def gateway(full_path: str, request: Request) -> Response:

    # find which service to call
    path = "/" + full_path
    target_base = _resolve_target(path)

    if target_base is None:
        return Response(content='{"detail":"Service not found"}', status_code=404,
                        media_type="application/json")

    # ── Rate limit check ──
    rejected = await check_rate_limit(request)
    if rejected:
        return Response(
            content=rejected["body"],
            status_code=rejected["status_code"],
            headers=rejected["headers"],
            media_type="application/json",
        )

    # ── Token blacklist check ──
    token = _extract_token_from_request(request)
    if token and await is_token_blacklisted("Bearer " + token):
        return Response(content='{"detail":"Token has been invalidated"}', status_code=401,
                        media_type="application/json")

    query = str(request.url.query) if request.url.query else ""

    # ── Cache check (GET only) ──
    if request.method == "GET":
        cached = await get_cached(path, query)
        if cached:
            body, status, content_type = cached
            return Response(content=body, status_code=status, media_type=content_type,
                            headers={"X-Cache": "HIT"})


    # construct the final url where request will be sent
    target_url = target_base.rstrip("/") + path.rstrip("/")
    if query:
        target_url += "?" + query

    # Forward all headers except 'host' (avoid host header mismatch)
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "cookie")
    }

    # Inject Authorization header from cookie if not already present

    # browser sends cookie: access_token=abc123 like this then gateway converts it to :  Authorization: bearer+token
    if token and "authorization" not in {k.lower() for k in headers}:
        headers["authorization"] = "Bearer " + token

    body = await request.body()
    # accepts user data


  # here gateway forwards request to actual service with same http method, same headers, same body
    async with httpx.AsyncClient(timeout=30.0) as client:
        proxy_response = await client.request(
            method=request.method,
            url=target_url,
            headers={
                **headers,
                "content-type": request.headers.get("content-type", "application/json"),
            },
            content=body,
        )

    # Filter out problematic headers  -- hop-by-hop headers that break the proxy
    excluded = {"content-encoding", "transfer-encoding", "content-length", "connection"}
    resp_headers = {
        k: v for k, v in proxy_response.headers.items()
        if k.lower() not in excluded
    }

    # ── Cache store (GET only, success responses) ──

    # store responses in redis cache 
    # adds header x-cache=miss means response came from backend
    if request.method == "GET":
        content_type = proxy_response.headers.get("content-type", "application/json")
        await set_cached(path, query, proxy_response.content, proxy_response.status_code, content_type)
        resp_headers["X-Cache"] = "MISS"

    # ── Cache invalidate (write operations) ──

    # if data changes clear cache  ensures consistency
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        await invalidate_cache(path)

    # ── Attach rate-limit info to response like limit, remaining-- helps frontend to understand how many requests are left 
    rl_headers = getattr(request.state, "rate_limit_headers", {})
    resp_headers.update(rl_headers)

    # final response send to frontend
    response = Response(
        content=proxy_response.content,
        status_code=proxy_response.status_code,
        headers=resp_headers,
        media_type=proxy_response.headers.get("content-type"),
    )

    # ── Set httpOnly cookie on successful login ──
    if path == "/auth/login" and proxy_response.status_code == 200:
        try:
            data = json.loads(proxy_response.content)
            access_token = data.get("access_token")

            # store token in browser cookie
            if access_token:
                response.set_cookie(
                    key=COOKIE_NAME,
                    value=access_token,
                    max_age=COOKIE_MAX_AGE,
                    httponly=True,  # means js cant see it
                    samesite="lax",  # prevent attacks
                    secure=False,  # set True in production with HTTPS
                    path="/",
                )
                # remove token from response body — cookie is the only channel
                data.pop("access_token", None)
                new_body = json.dumps(data).encode()
                response.body = new_body
                response.headers["content-length"] = str(len(new_body))
        except (json.JSONDecodeError, KeyError):
            pass

    return response
