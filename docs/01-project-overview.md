# 01 — Project Overview: Discussion Forum

## What Is This Project?

**In simple words:** This is a website like Reddit where people can:
- Create an account and log in
- Join communities (like subreddits)
- Post discussion threads inside communities
- Comment on threads (and reply to comments — nested like a tree)
- Like threads and comments
- Get real-time notifications (bell icon lights up instantly)
- Upload a profile picture (avatar)
- Search threads with keyword-based filtering
- Reset their password via email link
- Admins can manage users (activate/deactivate/delete), moderators can moderate content

**In interview terms:** This is a full-stack, microservices-based discussion platform built with:
- **Backend:** Python 3.13, FastAPI (async), PostgreSQL, Kafka, Redis, WebSockets
- **Frontend:** React 19, Material-UI (MUI), Axios, WebSocket API
- **Infrastructure:** Docker Compose (16 containers), Database-per-service pattern
- **Security:** JWT auth stored in httpOnly cookies, token blacklisting via Redis, sliding-window rate limiting, bcrypt password hashing, email-based password reset

---

## Architecture: The Big Picture

Imagine a restaurant:
- The **Frontend (React)** = the waiter taking your order
- The **API Gateway** = the manager who decides which kitchen section handles the order
- The **Microservices** = separate kitchen stations (one for pasta, one for salad, etc.)
- The **Databases** = each station's own storage/fridge
- **Kafka** = the intercom system so stations can notify each other
- **Redis** = the manager's notepad (caching, rate limits, token blacklist)

```
┌──────────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                         │
│                   http://localhost:3000                       │
│  15 Pages · Dark/Light Theme · Material-UI · WebSocket       │
└───────────────────────┬──────────────────────────────────────┘
                        │ HTTP (REST) + WebSocket
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                   API GATEWAY (:8000)                         │
│                                                              │
│  ✓ Routes requests to correct microservice                   │
│  ✓ Redis caching (GET) + auto cache invalidation             │
│  ✓ Sliding-window rate limiting (per client)                 │
│  ✓ JWT token blacklisting (logout)                           │
│  ✓ httpOnly cookie auth (sets cookie on login)               │
│  ✓ Token injection (cookie → Authorization header)           │
└───┬──────┬──────┬──────┬──────┬──────────────────────────────┘
    │      │      │      │      │
    ▼      ▼      ▼      ▼      ▼
┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
│ User ││Thread││Commt ││Commty││Notif │
│:8002 ││:8003 ││:8005 ││:8006 ││:8007 │
└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘
   │       │       │       │       │
   ▼       ▼       ▼       ▼       ▼
┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
│user  ││thread││commt ││commty││notif │
│_db   ││_db   ││_db   ││_db   ││_db   │
└──────┘└──────┘└──────┘└──────┘└──────┘

Infrastructure: Kafka + ZooKeeper + Redis + Mailpit
```

**Total containers: 16** = 5 databases + 5 microservices + 1 gateway + Kafka + ZooKeeper + Redis + Mailpit

---

## Why Microservices? (Interview Answer)

**Monolith:** Everything in one big app. If the notification system crashes, the whole app goes down.

**Microservices (what we use):** Each feature is a separate app:
- **User Service** handles only users, auth, profiles
- **Thread Service** handles only discussion threads and likes
- **Comment Service** handles only comments and replies
- **Community Service** handles only community CRUD and membership
- **Notification Service** handles only notifications and WebSockets

**Benefits for interview:**
1. **Independent deployment** — update thread service without touching user service
2. **Independent scaling** — if threads get heavy traffic, scale only that service
3. **Technology freedom** — each service could use a different language (we use Python for all)
4. **Fault isolation** — if notification service crashes, users can still post threads
5. **Database-per-service** — each service owns its data, no shared tables

**Trade-off:** More complex than a monolith (networking, data consistency, Docker setup). Worth it at scale, educational for learning.

---

## Tech Stack Breakdown

| Layer | Technology | Why We Use It |
|-------|-----------|---------------|
| **Frontend** | React 19 | Component-based UI, huge ecosystem |
| **UI Library** | Material-UI (MUI) | Pre-built responsive components, theming |
| **HTTP Client** | Axios | Promise-based, interceptors for auth |
| **Backend Framework** | FastAPI | Async Python, auto-generated docs, Pydantic validation |
| **ORM** | SQLAlchemy (async) | Python ↔ Database bridge, no raw SQL needed |
| **Database** | PostgreSQL 16 | Reliable, ACID-compliant relational DB |
| **Caching** | Redis 7 | In-memory store for cache, rate limits, token blacklist |
| **Message Broker** | Apache Kafka | Async event streaming between services |
| **Auth** | JWT (HS256) | Stateless tokens, 90-minute expiry |
| **Auth Storage** | httpOnly Cookies | XSS-safe — JavaScript cannot read the token |
| **Password Hashing** | bcrypt | Industry standard, slow hash = hard to brute-force |
| **Email (Dev)** | Mailpit | Catches all outgoing emails for testing (SMTP mock) |
| **Containerization** | Docker Compose | One command to start 16 containers |
| **Real-time** | WebSocket | Push notifications without polling |
| **Logging** | Python logging + RotatingFileHandler | Console + file logs with 5MB rotation |

---

## Port Reference

| Service | Port | URL |
|---------|------|-----|
| React Frontend | 3000 | http://localhost:3000 |
| API Gateway | 8000 | http://localhost:8000 |
| User & Auth Service | 8002 | http://localhost:8002 |
| Thread Service | 8003 | http://localhost:8003 |
| Comment Service | 8005 | http://localhost:8005 |
| Community Service | 8006 | http://localhost:8006 |
| Notification Service | 8007 | http://localhost:8007 |
| PostgreSQL (user) | 5433 | localhost:5433 |
| PostgreSQL (thread) | 5434 | localhost:5434 |
| PostgreSQL (comment) | 5436 | localhost:5436 |
| PostgreSQL (community) | 5437 | localhost:5437 |
| PostgreSQL (notification) | 5438 | localhost:5438 |
| Kafka | 9092/29092 | localhost:29092 (host) |
| ZooKeeper | 2181 | localhost:2181 |
| Redis | 6379 | localhost:6379 |
| Mailpit Web UI | 8025 | http://localhost:8025 |
| Mailpit SMTP | 1025 | localhost:1025 |

---

## User Roles & Permissions

| Action | Member | Moderator | Admin |
|--------|--------|-----------|-------|
| Create/edit own threads | ✅ | ✅ | ✅ |
| Create/edit own comments | ✅ | ✅ | ✅ |
| Like threads/comments | ✅ | ✅ | ✅ |
| Join/leave communities | ✅ | ✅ | ✅ |
| Report threads | ✅ | ✅ | ❌ (can delete directly) |
| View reports | ❌ | ✅ | ✅ |
| Delete any thread | ❌ | ✅ | ✅ |
| Delete any comment | ❌ | ✅ | ✅ |
| Edit any thread | ❌ | ❌ | ✅ |
| Change user roles | ❌ | ❌ | ✅ |
| Activate/deactivate users | ❌ | ❌ | ✅ |
| Delete users | ❌ | ❌ | ✅ |
| View all users | ❌ | ✅ (limited) | ✅ (full) |

---

## Environment Variables

These are set in `.env` at the project root and injected into Docker containers:

```
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=90
```

Each service also gets its own `DATABASE_URL` via docker-compose.yml. These are not in `.env` — they're hardcoded in the compose file because they reference Docker container hostnames.

---

## Seed Data

The project includes `backend/seed_data.py` which creates test users and content:

| User | Password | Role |
|------|----------|------|
| alice | pass123 | admin |
| bob | pass123 | moderator |
| charlie | pass123 | member |
| diana | pass123 | member |
| eve | pass123 | member |

On first boot, the user service automatically creates the `alice` admin account (bootstrap admin).

---

## Logging

Every service writes logs to:
1. **Console (stdout)** — visible via `docker compose logs <service>`
2. **Rotating file** — stored at `backend/logs/<service>/<service>.log`

Log files are volume-mounted to the host, so they persist across container restarts. Files rotate at 5MB with 3 backups.

**Format:** `2026-04-04 01:36:19,887 [service_name] INFO: message`
