# 04 — Thread Service (Port 8003)

## What Does This Service Do?

**Simple analogy:** This is the "bulletin board" where people post discussion topics. You can create a thread, tag it, like it, edit it, delete it, or report it.

**In interview terms:** The Thread Service manages discussion threads (CRUD), thread likes, and content reports. It supports keyword-based search, community filtering, pagination, and soft deletion. It publishes events to Kafka for real-time broadcasts.

---

## Database: `thread_db`

**Table: `threads`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-incrementing thread ID |
| `title` | String | Thread title (searchable) |
| `description` | Text | Thread body content |
| `tags` | String (nullable) | Comma-separated tags (searchable) |
| `status` | String | `open` (default) |
| `community_id` | Integer (nullable) | Which community this thread belongs to |
| `created_by` | Integer (FK → users.id) | Author's user ID |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last edit timestamp |
| `deleted_at` | DateTime (nullable) | Soft-delete timestamp |

**Table: `likes`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Like ID |
| `user_id` | Integer (FK) | Who liked |
| `thread_id` | Integer (FK, nullable) | Liked thread |
| `comment_id` | Integer (nullable) | Liked comment |
| `created_at` | DateTime | When liked |

**Constraint:** Exactly one of `thread_id` or `comment_id` must be non-null (check constraint). Plus a unique constraint prevents duplicate likes.

**Table: `reports`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Report ID |
| `thread_id` | Integer (FK) | Reported thread |
| `reported_by` | Integer (FK) | Who reported |
| `reason` | String | Reason category (e.g., spam, harassment) |
| `details` | Text (nullable) | Additional details |
| `status` | String | `pending`, `reviewed`, `dismissed` |
| `created_at` | DateTime | When reported |

---

## API Endpoints

### Thread CRUD

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/threads/` | Yes | Create a new thread |
| GET | `/threads/` | Yes | List threads (with search, filters, pagination) |
| GET | `/threads/{id}` | Yes | Get single thread with author info + like count |
| PUT | `/threads/{id}` | Yes | Update thread (owner or admin only) |
| DELETE | `/threads/{id}` | Yes | Soft-delete (owner, mod, or admin) |

### Search and Filtering

The GET `/threads/` endpoint supports:
- `search` — keyword-based (splits query into words, each word must appear in title OR description OR tags)
- `community_id` — filter by community
- `status` — filter by status
- `skip` / `limit` — pagination (default: 0, 20)

**Keyword search logic:** If you search "python async", it finds threads where BOTH "python" AND "async" appear (in title, description, or tags). This is more useful than substring matching.

### Likes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/threads/{id}/like` | Yes | Toggle like on a thread |
| GET | `/threads/{id}/like-status` | Yes | Check if current user liked this thread |

**Toggle behavior:** If you haven't liked → creates a like. If you already liked → removes the like. Returns the new like count.

### Reports

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/reports/` | Yes | Report a thread (reason + details) |
| GET | `/reports/` | Mod+ | List all reports (with status filter) |
| PUT | `/reports/{id}/status` | Mod+ | Update report status (reviewed/dismissed) |

---

## Kafka Events Published

| Event Type | Topic | When |
|------------|-------|------|
| `new_thread` | `thread-events` | Thread created (broadcast) |
| `thread_like_update` | `thread-events` | Thread liked/unliked (broadcast) |
| `thread_deleted` | `thread-events` | Thread soft-deleted (broadcast) |
| `thread_edited` | `thread-events` | Thread updated (broadcast) |

All events include `"broadcast": true` so the notification service pushes them to all connected WebSocket clients for real-time UI updates.

---

## Soft Delete

When a thread is deleted:
1. `deleted_at` is set to current timestamp
2. The thread no longer appears in listing queries (filtered by `deleted_at IS NULL`)
3. The data remains in the database for auditing
4. A Kafka event is broadcast so all clients remove it from their UI

**Who can delete:**
- Thread owner → can delete their own threads
- Moderator → can delete any thread
- Admin → can delete any thread

---

## File Structure

```
backend/services/thread_service/
├── app/
│   ├── main.py              # Lifespan, DB migration
│   ├── database.py          # Async SQLAlchemy engine + session
│   ├── kafka_producer.py    # Publishes thread events
│   ├── models/
│   │   ├── user.py          # User model (read-only, for relationships)
│   │   ├── thread.py        # Thread model
│   │   ├── like.py          # Like model (polymorphic)
│   │   └── report.py        # Report model
│   ├── schemas/
│   │   └── thread.py        # Pydantic schemas for create/update/response
│   ├── routes/
│   │   ├── thread_routes.py # Thread CRUD, likes, search
│   │   └── report_routes.py # Report CRUD
│   └── core/
│       ├── config.py        # Settings
│       ├── dependencies.py  # get_current_user()
│       ├── security.py      # JWT decode
│       ├── permissions.py   # Role checks
│       └── exceptions.py    # Custom HTTP exceptions
├── tests/
│   ├── conftest.py
│   └── test_threads.py
└── logs/
    └── thread_service.log
```

---

## Interview Q&A

**Q: Why keyword search instead of substring matching?**
A: Substring matching (`%python%`) is too broad — searching for "a" returns everything. Keyword search splits the query into words and requires ALL words to appear, giving more relevant results. For production, you'd use Elasticsearch or PostgreSQL full-text search.

**Q: Why is the Like model polymorphic?**
A: One `likes` table handles likes for threads, comments, and potentially posts using nullable foreign keys with a check constraint ensuring exactly one target. This avoids creating separate like tables for each content type.
