# 05 — Comment Service (Port 8005)

## What Does This Service Do?

**Simple analogy:** Under every bulletin board post (thread), people can leave comments. They can also reply to each other's comments, creating a nested tree of discussion — just like Reddit comment threads.

**In interview terms:** The Comment Service handles CRUD operations for comments on threads, supports nested replies (parent-child relationships), comment likes, and soft deletion. It publishes Kafka events for real-time broadcast.

---

## Database: `comment_db`

**Table: `comments`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Comment ID |
| `content` | Text | Comment body |
| `thread_id` | Integer | Which thread this comment belongs to |
| `author_id` | Integer (FK → users.id) | Who wrote it |
| `parent_comment_id` | Integer (FK → comments.id, nullable) | Parent comment (NULL = top-level) |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last edit timestamp |
| `deleted_at` | DateTime (nullable) | Soft-delete timestamp |

**Table: `likes`** (same structure as thread service)

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Like ID |
| `user_id` | Integer (FK) | Who liked |
| `comment_id` | Integer (nullable) | Liked comment |
| `created_at` | DateTime | When liked |

---

## Nested Comments (Threading)

Comments support a tree structure using `parent_comment_id`:

```
Thread: "Best Python frameworks?"
├── Comment 1: "FastAPI is great"                    (parent = NULL → top-level)
│   ├── Comment 3: "Agreed, async is fast"           (parent = 1 → reply to comment 1)
│   └── Comment 4: "But Flask is simpler"            (parent = 1 → reply to comment 1)
│       └── Comment 6: "True for small projects"     (parent = 4 → reply to comment 4)
├── Comment 2: "Django is solid"                     (parent = NULL → top-level)
│   └── Comment 5: "Django REST is nice too"         (parent = 2 → reply to comment 2)
```

The API returns comments as a flat list with `parent_comment_id`. The **frontend** builds the tree structure for rendering.

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/threads/{thread_id}/comments` | Yes | Create a comment (or reply) |
| GET | `/threads/{thread_id}/comments` | Yes | Get all comments for a thread |
| PUT | `/comments/{id}` | Yes | Edit comment (owner only) |
| DELETE | `/comments/{id}` | Yes | Soft-delete (owner, mod, or admin) |
| POST | `/comments/{id}/like` | Yes | Toggle like on a comment |
| GET | `/comments/{id}/like-status` | Yes | Check if current user liked |

**Creating a reply:** Send the same POST to `/threads/{thread_id}/comments` but include `parent_comment_id` in the body.

---

## Gateway Routing: Special Delegation

The URL `/threads/5/comments` belongs to the **Comment Service**, not the Thread Service. The gateway detects this:

```python
# In gateway's _resolve_target():
# If path is /threads/{id}/comments/* → route to comment_service
parts = path.strip("/").split("/")    # ["threads", "5", "comments"]
if len(parts) >= 3 and parts[0] == "threads":
    tail = "/" + "/".join(parts[2:])  # "/comments"
    # Match against comment_service delegation rules
```

---

## Kafka Events Published

| Event Type | Topic | When |
|------------|-------|------|
| `new_comment_broadcast` | `comment-events` | Comment created (broadcast to all) |
| `comment_like_update` | `comment-events` | Comment liked/unliked (broadcast) |
| `comment_deleted` | `comment-events` | Comment soft-deleted (broadcast) |
| `comment_edited` | `comment-events` | Comment updated (broadcast) |
| `new_comment` | `comment-events` | Personal notification to thread author |

**Two events on comment creation:**
1. `new_comment_broadcast` (broadcast = true) — all clients update their UI
2. `new_comment` (targeted) — thread author gets a personal notification

---

## File Structure

```
backend/services/comment_service/
├── app/
│   ├── main.py              # Lifespan, DB setup
│   ├── database.py          # Async SQLAlchemy
│   ├── kafka_producer.py    # Publishes comment events
│   ├── models/
│   │   ├── user.py          # User model (for relationships)
│   │   ├── comment.py       # Comment model (self-referencing FK)
│   │   └── like.py          # Like model
│   ├── schemas/
│   │   └── comment.py       # Pydantic schemas
│   ├── routes/
│   │   └── comment_routes.py # Comment CRUD, likes
│   ├── services/
│   │   └── comment_service.py
│   └── core/
│       ├── config.py, security.py, dependencies.py
│       ├── permissions.py, exceptions.py
├── tests/
│   ├── conftest.py
│   └── test_comments.py
└── logs/
    └── comment_service.log
```

---

## Interview Q&A

**Q: How do you handle nested comments?**
A: Using a self-referencing foreign key (`parent_comment_id`). Top-level comments have `parent_comment_id = NULL`. Replies point to their parent. The API returns a flat list; the frontend recursively builds the tree for rendering.

**Q: Why separate Comment Service from Thread Service?**
A: A thread might have hundreds of comments, and comment operations (create, edit, like) are much more frequent than thread operations. Separating them allows independent scaling — you can run 3 instances of the Comment Service while keeping 1 Thread Service instance.
