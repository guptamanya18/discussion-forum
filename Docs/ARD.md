# Architecture Reference Document (ARD)

## Advanced Real-Time Discussion Forum

| Field             | Value                                                |
|-------------------|------------------------------------------------------|
| **Project**       | Advanced Real-Time Discussion Forum (ThreadHub)      |
| **Architecture**  | Microservices                                        |
| **Version**       | 1.0                                                  |
| **Status**        | Development                                          |
| **Stack**         | FastAPI · React 19 · PostgreSQL 16 · Kafka · Redis   |

---

## Table of Contents

1. [Problem Statement & Goals](#1-problem-statement--goals)
2. [Architecture Style & Rationale](#2-architecture-style--rationale)
3. [System Architecture](#3-system-architecture)
4. [Service Decomposition](#4-service-decomposition)
5. [Technology Stack](#5-technology-stack)
6. [Data Management](#6-data-management)
7. [Communication Patterns](#7-communication-patterns)
8. [Authentication & Authorization](#8-authentication--authorization)
9. [Caching Strategy](#9-caching-strategy)
10. [Rate Limiting](#10-rate-limiting)
11. [Real-Time Features](#11-real-time-features)
12. [Testing Strategy](#12-testing-strategy)
13. [Deployment Architecture](#13-deployment-architecture)
14. [Logging & Observability](#14-logging--observability)
15. [Key Design Decisions & Trade-offs](#15-key-design-decisions--trade-offs)
16. [Non-Functional Requirements](#16-non-functional-requirements)
17. [Future Considerations](#17-future-considerations)

---

## 1. Problem Statement & Goals

### Problem

Build an advanced real-time discussion forum that supports communities, threaded conversations, real-time notifications, and role-based moderation — while maintaining independent scaling and deployment of each domain.

### Goals

| Goal                          | Description                                                              |
|-------------------------------|--------------------------------------------------------------------------|
| **Domain Isolation**          | Each business domain (users, threads, comments, communities, notifications) operates as an independent service with its own database |
| **Real-Time Experience**      | Instant UI updates for likes, new threads, comments, edits, and deletions via WebSocket |
| **Secure Authentication**     | httpOnly cookie-based JWT auth with token blacklisting on logout         |
| **Decoupled Communication**   | Event-driven architecture via Kafka — no direct service-to-service HTTP calls |
| **Operational Readiness**     | Centralized gateway for caching, rate limiting, and routing; structured logging per service |

---

## 2. Architecture Style & Rationale

### Style: Microservices + Event-Driven Architecture

| Aspect                | Decision                                              | Rationale                                                                 |
|-----------------------|-------------------------------------------------------|---------------------------------------------------------------------------|
| **Decomposition**     | 5 domain services + 1 API gateway                     | Single Responsibility — each service owns one business domain             |
| **Communication**     | Synchronous (HTTP via gateway) + Asynchronous (Kafka)  | Gateway handles client-facing requests; Kafka handles inter-service events |
| **Data Ownership**    | Database-per-service (5 isolated PostgreSQL instances) | No shared state; services can evolve schemas independently                |
| **Entry Point**       | API Gateway pattern                                   | Centralizes cross-cutting concerns (auth, caching, rate limiting, CORS)   |

### Alternatives Considered

| Alternative        | Why Rejected                                                                                      |
|--------------------|---------------------------------------------------------------------------------------------------|
| Monolith           | Tightly couples domains; scaling one domain means scaling everything                              |
| Shared Database    | Creates hidden coupling; schema changes in one service can break others                           |
| Direct HTTP Sync   | Creates tight temporal coupling; if User Service is down, all dependent services fail              |
| GraphQL Gateway    | Overhead for the current scope; REST is sufficient for CRUD-heavy forum operations                 |

---

## 3. System Architecture

### High-Level Architecture Diagram

```
+------------------------------------------------------------------+
|                        CLIENT LAYER                              |
|   +---------------------------+    +-------------------------+   |
|   |   React SPA (:3000)      |    |  Postman / curl / App   |   |
|   |  - 16 Pages (MUI 7)      |    +------------+------------+   |
|   |  - AuthContext + JWT      |                 |                |
|   |  - WebSocket Client       |                 |                |
|   +------------+--------------+                 |                |
|                |                                |                |
+----------------|--------------------------------|----------------+
                 |  HTTP / WebSocket              |
                 v                                v
+------------------------------------------------------------------+
|                     API GATEWAY (:8000)                           |
|   - Route resolution          - Redis caching (60s TTL)          |
|   - Sliding-window rate limit - JWT token blacklisting           |
|   - CORS handling             - Cookie ↔ Bearer conversion       |
+--+----------+----------+-----------+----------+------------------+
   |          |          |           |          |
   v          v          v           v          v
+------+  +------+  +--------+  +-------+  +---------+
| User |  |Thread|  |Comment |  |Commun.|  | Notif.  |
| :8002|  | :8003|  | :8005  |  | :8006 |  | :8007   |
+--+---+  +--+---+  +---+----+  +---+---+  +----+----+
   |         |           |          |            |
   v         v           v          v            v
+------+  +------+  +--------+  +-------+  +---------+
|user_ |  |thread|  |comment |  |commun.|  |notif._  |
|db    |  |_db   |  |_db     |  |_db    |  |db       |
+------+  +------+  +--------+  +-------+  +---------+

    Kafka (event bus)  ·  Redis (cache + rate limit + blacklist)
    Mailpit (dev email)  ·  ZooKeeper (Kafka coordination)
```

**Total: 15 Docker containers** = 5 PostgreSQL + 5 Services + 1 Gateway + Kafka + ZooKeeper + Redis + Mailpit

### Request Flow (Gateway)

```
Client Request → Gateway (:8000)
  ├── 1. Rate limit check (Redis sorted set)     → 429 if exceeded
  ├── 2. Token blacklist check (Redis)            → 401 if blacklisted
  ├── 3. Cache check (GET only, Redis)            → Return if HIT
  ├── 4. Route to target service                  → HTTP proxy
  ├── 5. Cache store (GET, on MISS)
  ├── 6. Cache invalidate (POST/PUT/DELETE)
  └── 7. Attach X-RateLimit-* and X-Cache headers
```

---

## 4. Service Decomposition

### 4.1 API Gateway (Port 8000)

| Responsibility         | Implementation                                                    |
|------------------------|-------------------------------------------------------------------|
| **Routing**            | URL path prefix matching → proxy to target service                |
| **Error Handling**     | **Standardized Custom Exception framework** for all proxy paths   |
| **Caching**            | Redis GET caching with `gw:` prefix, 60s TTL, write invalidation |
| **Rate Limiting**      | Redis sliding-window per-client (20/30/100 req/min by bucket)    |
| **Token Blacklisting** | JWT decode → Redis SETEX `bl:<token>` with remaining TTL         |
| **CORS**               | Configured for `http://localhost:3000`                            |
| **Cookie ↔ Bearer**    | Extracts JWT from httpOnly cookie, injects as Authorization header|

### 4.2 User & Auth Service (Port 8002)

| Responsibility           | Detail                                                          |
|--------------------------|-----------------------------------------------------------------|
| **Registration**         | Email validation, bcrypt hashing, Kafka events, 117 tests |
| **Login**                | Bcrypt verification, JWT (HS256, 90-min), httpOnly cookie       |
| **Profile Management**   | Bio, name, avatar upload (**strict MIME + Extension Check**)    |
| **Password Reset**       | 15-min JWT token via email (Mailpit SMTP), anti-enumeration     |
| **Admin Dashboard**      | User stats, listing, role changes, user deletion, toggle active |
| **Moderator Dashboard**  | Read-only user listing + stats                                  |
| **User Sync (Producer)** | Publishes `user_created` and `user_updated` Kafka events        |

### 4.3 Thread Service (Port 8003)

| Responsibility          | Detail                                                           |
|-------------------------|------------------------------------------------------------------|
| **CRUD**                | Create, read, update, soft-delete threads                        |
| **Likes**               | Toggle like/unlike with unique constraint per user               |
| **Search & Filter**     | Keyword search, tag filter, sort (hot/new/top), pagination       |
| **Role-Aware Delete**   | `ensure_can_delete()` — moderators cannot delete admin content   |
| **Kafka Events**        | `new_thread`, `thread_edited`, `thread_deleted`, `thread_like_update`, `thread_like` |

### 4.4 Comment Service (Port 8005)

| Responsibility          | Detail                                                           |
|-------------------------|------------------------------------------------------------------|
| **Comments & Replies**  | Unlimited nesting depth via `parent_comment_id`                  |
| **Comment Trees**       | Build nested tree structure for display                          |
| **Likes**               | Toggle with unique constraint                                    |
| **@Mentions**           | Regex-based mention detection                                    |
| **Cascading Delete**    | BFS traversal soft-deletes entire reply subtree                  |
| **Kafka Events**        | `new_comment_broadcast`, `comment_edited`, `comment_deleted`, `comment_like_update`, `comment_reply`, `comment_like` |

### 4.5 Community Service (Port 8006)

| Responsibility           | Detail                                                          |
|--------------------------|-----------------------------------------------------------------|
| **CRUD**                 | Create (auto-join as moderator), update, delete                 |
| **Membership**           | Join, leave, list members, role management                      |
| **Slug Generation**      | Auto-generated URL-friendly slugs                               |
| **Search**               | Keyword search + pagination with member counts                  |
| **Owner Protection**     | Cannot change community creator's role                          |
| **Kafka Events**         | `community_join`                                                |

### 4.6 Notification Service (Port 8007)

| Responsibility           | Detail                                                          |
|--------------------------|-----------------------------------------------------------------|
| **Kafka Consumer**       | **Fault-tolerant safety loop** for high-availability processing |
| **Real-time Push**       | Decoupled `thread-events`, `comment-events`, `community-events` |
| **Targeted Notifications** | Saved to DB + pushed via WebSocket to specific user            |
| **Broadcast Events**     | NOT saved — pushed to ALL connected WebSocket clients           |
| **WebSocket**            | `/ws?token=<JWT>` — real-time push with auto-reconnect         |
| **REST API**             | List notifications, unread count, mark read, mark all read      |

---

## 5. Technology Stack

### Backend

| Technology                | Version         | Purpose                                          |
|---------------------------|-----------------|--------------------------------------------------|
| **Python**                | 3.13            | Service language                                 |
| **FastAPI**               | latest          | Async REST framework                             |
| **SQLAlchemy**            | 2.x (async)    | ORM with async engine                            |
| **asyncpg**               | latest          | Async PostgreSQL driver                          |
| **PostgreSQL**            | 16-alpine       | Relational database (5 instances)                |
| **Kafka (Confluent)**     | 7.6.0           | Event message broker                             |
| **aiokafka**              | latest          | Async Kafka producer/consumer                    |
| **Redis**                 | 7-alpine        | Caching, rate limiting, token blacklisting       |
| **aioredis**              | latest          | Async Redis client (gateway)                     |
| **PyJWT**                 | latest          | JWT encoding/decoding (HS256)                    |
| **bcrypt / passlib**      | latest          | Password hashing                                 |
| **httpx**                 | latest          | Async HTTP client (gateway proxy)                |
| **python-multipart**      | latest          | File upload handling (avatars)                   |
| **aiosmtplib**            | latest          | Async SMTP client (password reset emails)        |
| **uvicorn**               | latest          | ASGI server                                      |
| **uv**                    | latest          | Fast package installer (10-100x faster than pip) |

### Frontend

| Technology                | Version         | Purpose                                          |
|---------------------------|-----------------|--------------------------------------------------|
| **React**                 | 19.x            | SPA framework                                    |
| **Material UI (MUI)**     | 7.x             | Component library (dark/light theme)             |
| **Axios**                 | latest          | HTTP client with cookie support                  |
| **React Router**          | v7              | Client-side routing with protected routes        |
| **notistack**             | latest          | Snackbar notification stack                      |
| **date-fns**              | latest          | Date formatting                                  |

### Infrastructure

| Technology                | Purpose                                              |
|---------------------------|------------------------------------------------------|
| **Docker Compose**        | Multi-container orchestration (15 containers)        |
| **Mailpit**               | Dev email capture (SMTP + Web UI)                    |
| **ZooKeeper**             | Kafka coordination                                   |

### Testing

| Technology                | Purpose                                              |
|---------------------------|------------------------------------------------------|
| **pytest**                | Test framework                                       |
| **pytest-asyncio**        | Async test support                                   |
| **httpx (AsyncClient)**   | Async HTTP testing against FastAPI test apps         |
| **SQLite (in-memory)**    | Isolated test databases (no Docker dependency)       |
| **unittest.mock**         | Kafka producer and external service mocking          |

---

## 6. Data Management

### 6.1 Database-Per-Service Pattern

Each service owns a dedicated PostgreSQL 16 instance. No service can access another service's database directly.

| Database           | Service              | Port  | Key Tables                                       |
|--------------------|----------------------|-------|--------------------------------------------------|
| `user_db`          | User Service         | 5433  | `users`                                          |
| `thread_db`        | Thread Service       | 5434  | `threads`, `likes`, `users` (local copy)         |
| `comment_db`       | Comment Service      | 5436  | `comments`, `likes`, `users` (local copy)        |
| `community_db`     | Community Service    | 5437  | `communities`, `community_members`, `users` (local) |
| `notification_db`  | Notification Service | 5438  | `notifications`, `users` (local copy)            |

### 6.2 Event-Driven User Sync (Event-Carried State Transfer)

Services that need user data (Thread, Comment, Community, Notification) maintain a **local `users` table** synchronized via Kafka events. There are **zero direct HTTP calls** between services for user data.

```
User Service                   Kafka (user-events topic)              Consumer Services
+-------------+                +---------------------+                +------------------+
| Registration |──user_created──>|                     |──consumed by──>| INSERT into      |
|              |                |                     |                | local users table|
| Profile Edit |──user_updated──>|                     |──consumed by──>| UPDATE local     |
|              |                |                     |                | users table      |
| Avatar Upload|──avatar_update─>|                     |──consumed by──>| UPDATE avatar    |
+-------------+                +---------------------+                +------------------+
```

**Why this pattern?**
- **Decoupled**: Consumer services work even if User Service is temporarily down
- **Fast reads**: No cross-service HTTP call needed for username/avatar lookups
- **Eventually consistent**: Small propagation delay (milliseconds via Kafka)

### 6.3 Soft Deletes

Threads and comments use a `deleted_at` timestamp instead of physical deletion:
- Preserves data for audit trails
- Maintains nested comment tree integrity
- Comments use BFS cascading soft-delete through the reply subtree

---

## 7. Communication Patterns

### 7.1 Synchronous — HTTP via API Gateway

```
Client → Gateway (:8000) → Target Service → PostgreSQL
```

All client-facing requests go through the gateway. The gateway transparently proxies headers, body, query params, and converts httpOnly cookies to Bearer tokens.

### 7.2 Asynchronous — Kafka Event Bus

| Kafka Topic          | Producer(s)         | Consumer              | Event Types                                                |
|----------------------|---------------------|-----------------------|------------------------------------------------------------|
| `user-events`        | User Service        | Thread, Comment, Community, Notification | `user_created`, `user_updated`, `avatar_update`  |
| `thread-events`      | Thread Service      | Notification Service  | `new_thread`, `thread_edited`, `thread_deleted`, `thread_like_update`, `thread_like` |
| `comment-events`     | Comment Service     | Notification Service  | `new_comment_broadcast`, `comment_edited`, `comment_deleted`, `comment_like_update`, `comment_reply`, `comment_like` |
| `community-events`   | Community Service   | Notification Service  | `community_join`                                           |

### 7.3 Real-Time — WebSocket

The Notification Service maintains WebSocket connections with all authenticated clients:

- **Targeted events**: Saved to DB, pushed to one specific user (likes, replies, mentions)
- **Broadcast events**: NOT saved, pushed to ALL connected clients (new threads, edits, deletes, like count changes)

### 7.4 Communication Matrix

| From → To              | Protocol   | Purpose                                    |
|------------------------|------------|--------------------------------------------|
| Client → Gateway       | HTTP/WS    | All API requests + WebSocket connection     |
| Gateway → Services     | HTTP       | Transparent proxy                           |
| Services → Kafka       | Kafka      | Event publishing (async)                    |
| Kafka → Notification   | Kafka      | Event consumption + WebSocket push          |
| Kafka → Thread/Comment/Community | Kafka | User sync events                   |
| Notification → Client  | WebSocket  | Real-time push                              |
| User Service → Mailpit | SMTP       | Password reset emails                       |
| Gateway → Redis        | Redis      | Cache, rate limit, token blacklist          |

---

## 8. Authentication & Authorization

### 8.1 Authentication Flow

```
1. POST /auth/login (username + password as form-data)
2. User Service verifies bcrypt hash
3. Generates JWT (HS256, 90-min expiry, payload: {"sub": "<user_id>"})
4. Gateway sets token as httpOnly cookie (not in response body)
5. Browser sends cookie automatically on every request
6. Gateway extracts token from cookie → injects as Authorization: Bearer header
7. Target service validates JWT and extracts user_id
```

**Security properties:**
- Token NOT accessible via JavaScript (httpOnly)
- Token NOT stored in localStorage (XSS-proof)
- Token blacklisted on logout (Redis SETEX with remaining TTL)

### 8.2 Token Lifecycle

| Event              | Action                                                     |
|--------------------|------------------------------------------------------------|
| **Login**          | JWT created → set as httpOnly cookie                       |
| **Each Request**   | Cookie → Bearer conversion by gateway                      |
| **Blacklist Check**| Gateway checks `EXISTS bl:<token>` in Redis               |
| **Logout**         | `SETEX bl:<token> <remaining_ttl>` → delete cookie        |
| **Expiry**         | JWT naturally expires after 90 minutes                     |
| **Password Reset** | Separate 15-min JWT sent via email (not stored)            |

### 8.3 Role-Based Access Control (RBAC)

Three system-level roles: **Member**, **Moderator**, **Admin**

| Action                             | Member | Moderator | Admin |
|------------------------------------|--------|-----------|-------|
| View content, create threads/comments | ✓    | ✓         | ✓     |
| Like threads and comments          | ✓      | ✓         | ✓     |
| Edit / Delete own content          | ✓      | ✓         | ✓     |
| Delete members' content            | ✗      | ✓         | ✓     |
| Delete moderator/admin content     | ✗      | ✗         | ✓     |
| View user lists + mod stats        | ✗      | ✓         | ✓     |
| Change user roles / Delete users   | ✗      | ✗         | ✓     |

### 8.4 Delete Permission Matrix

The `ensure_can_delete()` utility enforces role-aware deletion:

| Deleter Role | Member Content | Moderator Content | Admin Content |
|--------------|:--------------:|:-----------------:|:-------------:|
| Member       | Own only       | ✗                 | ✗             |
| Moderator    | ✓              | Own only          | ✗             |
| Admin        | ✓              | ✓                 | ✓             |

---

## 9. Caching Strategy

### Gateway-Level Redis Caching

| Aspect            | Detail                                              |
|-------------------|-----------------------------------------------------|
| **Scope**         | Gateway-evel (centralized invalidation control)     |
| **Key Prefix**    | `gw:<METHOD>:<full_url>` (Collision-safe)          |
| **TTL**           | 60 seconds (Configurable per environment)          |
| **Invalidation**  | **Mapping-driven** (Clears list + details on write) |
| **Headers**       | `X-Cache: HIT` or `X-Cache: MISS`                   |
| **Monitoring**    | `GET /cache-stats` returns active keys + TTL        |

### Cache Invalidation Strategy

Write operations invalidate cache entries matching the same URL path prefix. Example: `POST /threads` invalidates all `gw:GET:/threads*` keys.

---

## 10. Rate Limiting

### Sliding-Window Algorithm (Redis Sorted Sets)

Each client gets a Redis sorted set keyed by `rl:<client_ip>:<bucket>`. Requests older than 60 seconds are pruned on each check.

| Bucket   | Endpoints                          | Limit      |
|----------|------------------------------------|------------|
| `auth`   | `/auth/*` (login, register, reset) | 20 req/min |
| `write`  | POST/PUT/PATCH/DELETE on any route | 30 req/min |
| `read`   | All GET requests                   | 100 req/min|

### Response Headers (every request)

| Header                  | Description                          |
|-------------------------|--------------------------------------|
| `X-RateLimit-Limit`     | Maximum requests allowed in window   |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Reset`     | Timestamp when window resets         |

Returns `429 Too Many Requests` when limit exceeded.

---

## 11. Real-Time Features

### WebSocket Architecture

```
Browser (React)
    |
    | ws://localhost:8007/ws?token=<JWT>
    v
Notification Service (:8007)
    |
    ├── Authenticates JWT from httpOnly cookie (or ?token= fallback)
    ├── Registers client in WebSocket manager
    ├── Kafka consumer processes events
    |   ├── Targeted event → save to DB + push to specific user
    |   └── Broadcast event → push to ALL connected clients
    └── Auto-reconnect: exponential backoff (1s → 30s max)
```

### Broadcast Events (real-time UI updates, not persisted)

| Event                    | Trigger                          | UI Effect                         |
|--------------------------|----------------------------------|-----------------------------------|
| `new_thread`             | Thread created                   | Add to thread list                |
| `thread_edited`          | Thread updated                   | Update title/description/tags     |
| `thread_deleted`         | Thread soft-deleted              | Remove from list                  |
| `thread_like_update`     | Thread liked/unliked             | Update like count                 |
| `new_comment_broadcast`  | Comment created                  | Add to comment tree               |
| `comment_edited`         | Comment updated                  | Update comment content            |
| `comment_deleted`        | Comment soft-deleted             | Remove from tree                  |
| `comment_like_update`    | Comment liked/unliked            | Update like count                 |
| `avatar_update`          | User changed avatar              | Refresh avatar across UI          |

### Targeted Events (persisted + pushed to one user)

| Event              | Trigger                    | Notification                        |
|--------------------|----------------------------|-------------------------------------|
| `thread_like`      | Someone liked your thread  | "X liked your thread"               |
| `comment_reply`    | Reply to your comment      | "X replied to your comment"         |
| `comment_like`     | Someone liked your comment | "X liked your comment"              |
| `community_join`   | Someone joined your community | "X joined your community"        |

---

## 12. Testing Strategy

### Overview

| Metric              | Value                                    |
|---------------------|------------------------------------------|
| **Total Tests**     | 117                                      |
| **Framework**       | pytest + pytest-asyncio                  |
| **HTTP Client**     | httpx AsyncClient (against FastAPI app)  |
| **Test Database**   | SQLite in-memory (no Docker needed)      |
| **Kafka Mocking**   | `unittest.mock.AsyncMock` on producer    |
| **External Mocks**  | Service URLs patched to prevent HTTP calls |

### Test Distribution

| Service              | Tests | Coverage Areas                                                   |
|----------------------|-------|------------------------------------------------------------------|
| **User Service**     | 29    | Registration, login, auth validation, profile, admin CRUD, mod endpoints, password reset |
| **Thread Service**   | 28    | CRUD, search, sort, tags, likes, role-aware delete, reports      |
| **Community Service**| 27    | CRUD, slug, search, join/leave, role management, owner protection |
| **Comment Service**  | 20    | CRUD, replies, comment trees, likes, cascading delete, batch counts |
| **Notification Service** | 13 | Emit, list, pagination, unread count, mark read, auth           |

### Testing Approach

- **Isolation**: Each test gets a fresh SQLite in-memory database via `conftest.py` fixtures
- **No Docker**: Tests run independently — Kafka producer mocked, service URLs patched
- **Async**: All tests use `pytest-asyncio` with `httpx.AsyncClient` for true async testing
- **Fixtures**: Shared user creation + login fixtures for auth token generation

---

## 13. Deployment Architecture

### Docker Compose (Development)

15 containers orchestrated via `docker-compose.yml`:

| Category         | Containers                                              | Count |
|------------------|---------------------------------------------------------|-------|
| **Databases**    | postgres_user, postgres_thread, postgres_comment, postgres_community, postgres_notification | 5 |
| **Services**     | user_service, thread_service, comment_service, community_service, notification_service | 5 |
| **Gateway**      | gateway                                                 | 1     |
| **Messaging**    | kafka, zookeeper                                        | 2     |
| **Cache**        | redis                                                   | 1     |
| **Dev Tools**    | mailpit                                                 | 1     |

### Health Checks & Dependency Management

| Container       | Health Check                              | Interval |
|-----------------|-------------------------------------------|----------|
| PostgreSQL (×5) | `pg_isready -U forum_user -d <db>`        | 5s, 5 retries |
| Kafka           | `kafka-broker-api-versions`               | 10s, 5 retries |
| Redis           | `redis-cli ping`                          | 5s, 5 retries |

Services use `depends_on: condition: service_healthy` to ensure infrastructure is ready before startup.

### Port Map

| Port  | Service                  |
|-------|--------------------------|
| 3000  | React Frontend (local)   |
| 8000  | API Gateway              |
| 8002  | User & Auth Service      |
| 8003  | Thread Service           |
| 8005  | Comment Service          |
| 8006  | Community Service        |
| 8007  | Notification Service     |
| 9092  | Kafka (internal)         |
| 6379  | Redis                    |
| 8025  | Mailpit Web UI           |
| 5433–5438 | PostgreSQL instances |

---

## 14. Logging & Observability

### Structured Logging

| Aspect         | Detail                                                      |
|----------------|-------------------------------------------------------------|
| **Handler**    | `RotatingFileHandler` (Python `logging` module)             |
| **Max Size**   | 5 MB per file                                               |
| **Backups**    | 3 rotated files per service                                 |
| **Format**     | `%(asctime)s [%(name)s] %(levelname)s: %(message)s`         |
| **Output**     | Console (stdout) + file simultaneously                      |
| **Volume Mount** | Container logs mapped to `backend/logs/<service>/` on host |

### Log Directory Structure

```
backend/logs/
├── gateway/              → gateway.log
├── user_service/         → user_service.log
├── thread_service/       → thread_service.log
├── comment_service/      → comment_service.log
├── community_service/    → community_service.log
└── notification_service/ → notification_service.log
```

### Monitoring Endpoints

| Endpoint          | Service  | Description                     |
|-------------------|----------|---------------------------------|
| `GET /health`     | Gateway  | Service URLs + Redis status     |
| `GET /cache-stats`| Gateway  | Cached Redis keys with TTL      |
| `GET /health`     | All 5    | Per-service health check        |

---

## 15. Key Design Decisions & Trade-offs

| #  | Decision                          | Rationale                                                                     | Trade-off                                              |
|----|-----------------------------------|-------------------------------------------------------------------------------|--------------------------------------------------------|
| 1  | **API Gateway Pattern**           | Single entry point centralizes caching, rate limiting, auth, CORS             | Single point of failure; added latency per request     |
| 2  | **Database-Per-Service**          | True isolation; independent schema evolution                                  | Data duplication; no cross-service joins               |
| 3  | **Event-Driven User Sync**        | Zero HTTP dependency between services; works even if User Service is down     | Eventually consistent (ms delay); local data can be stale |
| 4  | **Kafka over RabbitMQ**          | Durable, ordered log; supports replay; better for event sourcing patterns     | Higher operational complexity; ZooKeeper dependency     |
| 5  | **Redis Triple-Duty**            | One Redis instance for cache + rate limit + blacklist; resource efficient      | Single Redis failure affects all three capabilities    |
| 6  | **httpOnly Cookie JWT**           | XSS-proof — token never accessible to JavaScript                              | Requires cookie-to-Bearer conversion in gateway       |
| 7  | **Token Blacklisting**           | Immediate logout despite stateless JWT                                        | Redis dependency for every authenticated request       |
| 8  | **Soft Deletes**                 | Audit trail preservation; comment tree integrity                              | Deleted data still in DB; queries need `WHERE deleted_at IS NULL` |
| 9  | **Sliding-Window Rate Limiting** | More accurate than fixed windows; prevents burst-at-boundary attacks          | Higher Redis memory usage (sorted set per client)      |
| 10 | **WebSocket Broadcast + Targeted**| Real-time UX; broadcasts avoid per-user DB writes for UI update events       | Broadcast events lost if client is disconnected        |
| 11 | **SQLite for Tests**             | Fast, no Docker dependency, isolated per test                                 | Minor dialect differences from PostgreSQL              |
| 12 | **Saved Posts in localStorage**  | Zero backend cost; instant; private to browser                                | Not synced across devices; lost on browser data clear  |
| 13 | **uv Package Manager**          | 10-100x faster than pip in Docker builds                                     | Newer tool; less community documentation               |

---

## 16. Non-Functional Requirements

| Requirement        | Implementation                                                             |
|--------------------|----------------------------------------------------------------------------|
| **Scalability**    | Microservices can scale independently; Kafka partitions support horizontal scaling |
| **Availability**   | Health checks + dependency ordering ensure clean startup; services restart on failure |
| **Performance**    | Redis caching (60s TTL), async I/O throughout (FastAPI + asyncpg + aiokafka), uv for fast builds |
| **Security**       | httpOnly JWT cookies (XSS-proof), bcrypt hashing, token blacklisting, anti-enumeration on password reset, role-aware permissions, CORS restricted |
| **Maintainability**| Database-per-service isolation, structured logging, 117 automated tests, consistent project structure |
| **Observability**  | Per-service rotating logs, health endpoints, cache stats, rate limit headers |

---

## 17. Future Considerations

| Area                     | Potential Enhancement                                              |
|--------------------------|--------------------------------------------------------------------|
| **Container Orchestration** | Migrate from Docker Compose to Kubernetes for production         |
| **API Gateway**          | Replace custom gateway with Kong / Traefik for production features |
| **Monitoring**           | Add Prometheus + Grafana for metrics; ELK stack for log aggregation |
| **Search**               | Replace SQL LIKE queries with Elasticsearch for full-text search   |
| **CI/CD**                | GitHub Actions pipeline for automated testing + Docker image builds |
| **Database**             | Add read replicas for high-traffic services; connection pooling    |
| **Caching**              | Redis Cluster for high availability; cache warming strategies      |
| **Security**             | Add refresh token rotation; implement CSRF tokens for mutations    |
| **Event Processing**     | Add dead letter queues for failed Kafka event processing           |
| **Frontend**             | Server-side rendering (Next.js) for SEO; PWA capabilities          |
