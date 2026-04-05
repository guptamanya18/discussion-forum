# 07 — Notification Service (Port 8005)

## What Does This Service Do?

**Simple analogy:** Think of Instagram notifications — when someone likes your post or comments on it, you see a bell icon with a red badge. This service does exactly that, but using **real-time WebSockets** (instant push) backed by **Kafka events** (event-driven architecture).

**In interview terms:** The Notification Service is an event-driven microservice that consumes Kafka events from other services, persists notifications in a database, and pushes them in real-time to connected clients via WebSocket. It supports both **targeted** (to one user) and **broadcast** (to all connected clients) notifications.

---

## Database: `notification_db`

**Table: `notifications`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Notification ID |
| `user_id` | Integer (indexed) | Who this notification is for |
| `type` | String | Event type (e.g., "comment", "like", "community_join") |
| `message` | String | Human-readable message |
| `reference_id` | Integer (nullable) | Link to the related entity (thread ID, comment ID, etc.) |
| `is_read` | Boolean (default false) | Whether the user has seen it |
| `created_at` | DateTime | When it was created |

---

## Two Delivery Mechanisms

### 1. Kafka Consumer (Primary)

The service subscribes to **4 Kafka topics**:

| Topic | Example Events |
|-------|---------------|
| `thread-events` | New thread created, thread liked, thread edited, thread deleted |
| `comment-events` | New comment, comment liked, comment edited, comment deleted |
| `community-events` | User joined community, user left community |
| `user-events` | Avatar updated |

**Broadcast vs. Targeted:**

- **Broadcast events** (`event.broadcast == true`): Sent to ALL connected WebSocket clients. Not saved to DB. Used for real-time UI updates like like counts, new threads/comments appearing live, avatar changes.
- **Targeted events** (`event.user_id` is set): Saved to DB and pushed to that specific user's WebSocket. Example: "Alice commented on your thread."

### 2. Internal HTTP Endpoint (`POST /notifications/emit`)

Other services can call this endpoint directly to create + push a notification. Not commonly used since Kafka handles most events, but available as a fallback.

---

## WebSocket System

### Connection Flow

```
1. User opens app → Frontend opens WebSocket: ws://localhost:8000/notifications/ws
2. Gateway proxies to notification service port 8005
3. Service reads JWT from httpOnly cookie (fallback: ?token= query param)
4. JWT decoded → user_id extracted → connection registered in ConnectionManager
5. Service sends ping every 30s to keep connection alive
6. On disconnect → connection removed from manager
```

### ConnectionManager

The `ConnectionManager` class manages all active WebSocket connections:

```python
active_connections: dict[int, list[WebSocket]]
#                        ↑              ↑
#                   user_id    list (one user can have multiple tabs)
```

**Key methods:**
- `connect(user_id, ws)` — Accepts WebSocket, adds to user's connection list
- `disconnect(user_id, ws)` — Removes a specific connection
- `send_to_user(user_id, data)` — Sends JSON to all of a user's connections (multi-tab support)
- `broadcast(data)` — Sends JSON to ALL connected clients across all users

**Dead connection cleanup:** If sending to a WebSocket fails, it's removed from the list automatically.

### Cookie-Based Authentication

```python
# Read JWT from cookie header (browsers send cookies automatically for WS)
cookie_header = websocket.headers.get("cookie", "")
cookie = SimpleCookie()
cookie.load(cookie_header)
token = cookie["access_token"].value
```

The WebSocket endpoint first checks the cookie header, then falls back to the `?token=` query parameter.

---

## REST API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/notifications/emit` | No (internal) | Create + push a notification |
| GET | `/notifications` | Yes | List user's notifications (paginated) |
| GET | `/notifications/unread-count` | Yes | Get count of unread notifications |
| PUT | `/notifications/{id}/read` | Yes | Mark one notification as read |
| PUT | `/notifications/read-all` | Yes | Mark all notifications as read |

### Pagination

`GET /notifications?skip=0&limit=30` returns:
```json
{
  "items": [...],
  "total": 42
}
```

---

## Broadcast Event Examples

| Event Type | What Happens | Data Included |
|------------|-------------|---------------|
| `thread_liked` / `thread_unliked` | Like counter updates in real-time | `thread_id`, `like_count` |
| `comment_liked` / `comment_unliked` | Comment like counter updates | `comment_id`, `like_count` |
| `thread_created` | New thread appears on page | Full `thread` object |
| `comment_created` | New comment appears | Full `comment` object |
| `thread_edited` | Thread content updates live | `thread_id`, `title`, `description`, `tags` |
| `comment_edited` | Comment content updates live | `comment_id`, `content` |
| `thread_deleted` | Thread removed from view | `thread_id`, `deleted_count` |
| `comment_deleted` | Comment removed from view | `comment_id`, `deleted_count` |
| `avatar_updated` | User avatar refreshes | `user_id`, `avatar` |

---

## File Structure

```
backend/services/notification_service/
├── app/
│   ├── main.py                # Lifespan, Kafka consumer startup
│   ├── database.py            # Async SQLAlchemy
│   ├── kafka_consumer.py      # Consumes 4 Kafka topics
│   ├── ws_manager.py          # ConnectionManager (send_to_user, broadcast)
│   ├── models/
│   │   ├── user.py            # User model (read-only)
│   │   └── notification.py    # Notification model
│   ├── schemas/
│   │   └── notification.py    # NotificationEmit, NotificationResponse, UnreadCount
│   ├── routes/
│   │   ├── notification_routes.py  # REST endpoints + emit
│   │   └── ws_routes.py           # WebSocket endpoint with cookie auth
│   └── core/
│       ├── config.py, security.py, dependencies.py
│       └── exceptions.py
└── logs/
    └── notification_service.log
```

---

## Interview Q&A

**Q: Why use Kafka for notifications instead of direct HTTP calls?**
A: Kafka decouples services. The thread service publishes a "thread_created" event and doesn't need to know which services consume it. If the notification service is down, events queue up in Kafka and get processed when it recovers (at-least-once delivery).

**Q: What's the difference between broadcast and targeted notifications?**
A: Broadcasts go to all connected clients for real-time UI sync (like counts, new posts appearing). They are NOT saved to the database. Targeted notifications go to a specific user, ARE saved to the database, and appear in the notification bell.

**Q: How does WebSocket auth work with httpOnly cookies?**
A: Browsers automatically send cookies with WebSocket upgrade requests. The service reads the `cookie` header from the WebSocket handshake, parses it, and extracts the JWT. This avoids exposing the token in the URL as a query parameter.

**Q: What if a user has multiple tabs open?**
A: The `ConnectionManager` stores a list of WebSocket connections per user. When sending to a user, it iterates over all their connections. Dead connections are cleaned up automatically.
