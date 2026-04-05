# 09 — Testing & Commands

## Testing Overview

Three services have async test suites:

| Service | Test File | Tests |
|---------|-----------|-------|
| User Service | `tests/test_users.py` | Registration, login, profile, admin CRUD |
| Thread Service | `tests/test_threads.py` | Thread CRUD, search, likes, reports |
| Comment Service | `tests/test_comments.py` | Comment CRUD, nested replies, likes |

### Test Stack

| Tool | Purpose |
|------|---------|
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support (mode = "auto") |
| `httpx.AsyncClient` | In-process HTTP client (no real server needed) |
| `aiosqlite` | In-memory SQLite for test DB (no PostgreSQL needed) |
| `unittest.mock` | Mock Kafka producer (no real Kafka needed) |

### How Tests Work

```
1. conftest.py creates an in-memory SQLite engine
2. Overrides the FastAPI get_db dependency with the test DB
3. Mocks the Kafka producer (no real Kafka during tests)
4. Before each test: creates all tables
5. After each test: drops all tables (clean slate)
6. auth_token fixture: creates a user in DB + generates a valid JWT
```

**Key insight:** Tests run entirely in-memory with no external dependencies — no Docker, no PostgreSQL, no Kafka, no Redis.

### Running Tests

```bash
# From a service directory (e.g., comment_service):
cd backend/services/comment_service

# Install test dependencies:
pip install -e ".[test]"

# Run all tests:
pytest -v

# Run a specific test:
pytest tests/test_comments.py::test_like_toggle -v

# Run with print output:
pytest -v -s
```

---

## Docker Commands

### Build & Start Everything

```bash
# Build and start all containers (first time or after code changes):
docker compose up --build -d

# Start without rebuilding:
docker compose up -d

# Stop everything:
docker compose down

# Stop and remove volumes (DELETE ALL DATA):
docker compose down -v
```

### View Logs

```bash
# All services:
docker compose logs -f

# Specific service:
docker compose logs -f gateway
docker compose logs -f user-service
docker compose logs -f thread-service
docker compose logs -f comment-service
docker compose logs -f community-service
docker compose logs -f notification-service

# Last 100 lines of a service:
docker compose logs --tail=100 gateway
```

### Rebuild a Single Service

```bash
# Rebuild only the gateway:
docker compose up --build -d gateway

# Rebuild only user-service:
docker compose up --build -d user-service
```

### Container Status

```bash
# List running containers:
docker compose ps

# Check health:
docker compose ps --format "table {{.Name}}\t{{.Status}}"
```

---

## Database Commands

Each service has its own PostgreSQL database:

| Service | DB Name | Port |
|---------|---------|------|
| User Service | `user_db` | 5433 |
| Thread Service | `thread_db` | 5434 |
| Comment Service | `comment_db` | 5435 |
| Community Service | `community_db` | 5436 |
| Notification Service | `notification_db` | 5437 |

```bash
# Connect to a database (from host):
docker compose exec user-db psql -U postgres -d user_db

# Example SQL queries:
SELECT * FROM users;
SELECT * FROM threads WHERE status = 'open';
SELECT * FROM comments WHERE thread_id = 1;
SELECT * FROM communities;
SELECT * FROM notifications WHERE is_read = false;

# Exit psql:
\q
```

---

## Seed Data

The `seed_data.py` script populates the forum with sample data:

```bash
# Prerequisites:
pip install httpx

# Run (all services must be up):
python backend/seed_data.py
```

**What it creates:** Sample users, communities, threads, comments, and likes. Uses the gateway API so everything goes through the normal flow.

---

## Useful API Calls (PowerShell/cURL)

### Login

```powershell
# PowerShell:
$response = Invoke-WebRequest -Uri "http://localhost:8000/auth/login" `
  -Method POST `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=alice@example.com&password=pass123" `
  -SessionVariable session

# The session variable now holds the httpOnly cookie
# Use it for subsequent requests:
Invoke-WebRequest -Uri "http://localhost:8000/auth/me" -WebSession $session
```

```bash
# cURL:
curl -c cookies.txt -X POST http://localhost:8000/auth/login \
  -d "username=alice@example.com&password=pass123"

# Use the cookie for subsequent requests:
curl -b cookies.txt http://localhost:8000/auth/me
```

### Health Check

```bash
# Check gateway:
curl http://localhost:8000/health

# Check individual services:
curl http://localhost:8001/health  # user
curl http://localhost:8002/health  # thread
curl http://localhost:8003/health  # comment
curl http://localhost:8004/health  # community (actually port may vary)
curl http://localhost:8005/health  # notification
```

---

## Log Files

Persistent log files are volume-mounted to the host:

```
backend/logs/
├── user_service/
│   └── user_service.log         # 5MB max, 3 backups
├── thread_service/
│   └── thread_service.log
├── comment_service/
│   └── comment_service.log
├── community_service/
│   └── community_service.log
├── notification_service/
│   └── notification_service.log
└── gateway/
    └── gateway.log
```

```bash
# View live logs on host:
Get-Content backend/logs/gateway/gateway.log -Tail 50 -Wait    # PowerShell
tail -f backend/logs/gateway/gateway.log                        # Linux/Mac
```

---

## Common Issues & Fixes

| Problem | Solution |
|---------|----------|
| Container won't start | `docker compose logs <service>` — check for DB connection errors |
| 502 Bad Gateway | A backend service is down. Check `docker compose ps` |
| CORS errors | Ensure `withCredentials: true` in frontend and gateway allows origin |
| Token expired | Login again — tokens expire after 90 minutes |
| Test DB errors | Run `pip install -e ".[test]"` to install aiosqlite |
| Kafka consumer not receiving | Check Kafka container is healthy: `docker compose logs kafka` |
| Stale frontend | `cd frontend && npm start` — dev server auto-reloads |
