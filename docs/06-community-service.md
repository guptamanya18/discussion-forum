# 06 — Community Service (Port 8006)

## What Does This Service Do?

**Simple analogy:** Communities are like subreddits — groups around a specific topic. You can create a community called "Python Developers", invite people to join, and post threads inside it. Only members can post.

**In interview terms:** The Community Service manages community CRUD, membership (join/leave), and generates URL-friendly slugs. It uses slug-based identification in URLs for SEO and readability.

---

## Database: `community_db`

**Table: `communities`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Community ID |
| `name` | String (unique) | Community name |
| `slug` | String (unique) | URL-friendly version (e.g., "python-developers") |
| `description` | Text (nullable) | What the community is about |
| `created_by` | Integer (FK → users.id) | Who created it |
| `created_at` | DateTime | Creation timestamp |

**Table: `community_members`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Membership ID |
| `user_id` | Integer (FK) | Member's user ID |
| `community_id` | Integer (FK) | Community ID |
| `role` | String | Member's role in the community (default: "member") |
| `joined_at` | DateTime | When they joined |

**Constraint:** `UNIQUE(user_id, community_id)` — a user can't join the same community twice.

---

## Slug System

URLs use slugs instead of numeric IDs for readability:
- **Before:** `/communities/5`
- **After:** `/communities/python-developers`

**Slug generation:**
```python
"Python Developers!"  →  "python-developers"
"Web   Dev & Design"  →  "web-dev-design"
"C++ Programming"     →  "c-programming"
```

Rules: lowercase, spaces→hyphens, special chars removed, multiple hyphens collapsed.

**Uniqueness:** If "python-dev" already exists, the system appends a counter: "python-dev-2", "python-dev-3".

**API accepts both:** All endpoints work with either the slug or numeric ID. The `_resolve_community()` helper tries numeric first, then slug lookup.

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/communities/` | Yes | Create a new community |
| GET | `/communities/` | Yes | List all communities |
| GET | `/communities/{slug}` | Yes | Get single community with member count |
| PUT | `/communities/{slug}` | Yes | Update community (owner only) |
| DELETE | `/communities/{slug}` | Yes | Delete community (owner or admin) |
| POST | `/communities/{slug}/join` | Yes | Join a community |
| DELETE | `/communities/{slug}/leave` | Yes | Leave a community |
| GET | `/communities/{slug}/members` | Yes | List community members |
| GET | `/communities/my/communities` | Yes | List communities I own or belong to |

---

## Membership Rules

- **Owner:** The user who created the community. They are auto-added as a member on creation.
- **Joining:** Any logged-in user can join any community.
- **Leaving:** Any member can leave. Owners can leave too (but the community stays).
- **Join Button:** Hidden for community owners on the listing page (you can't "join" what you own).

---

## Kafka Events Published

| Event Type | Topic | When |
|------------|-------|------|
| `community_join` | `community-events` | User joins a community |
| `community_leave` | `community-events` | User leaves a community |

---

## File Structure

```
backend/services/community_service/
├── app/
│   ├── main.py              # Lifespan, slug migration + backfill
│   ├── database.py          # Async SQLAlchemy
│   ├── kafka_producer.py    # Publishes community events
│   ├── models/
│   │   ├── user.py          # User model
│   │   ├── community.py     # Community model + generate_slug()
│   │   └── community_member.py # Membership model
│   ├── schemas/
│   │   └── community.py     # Pydantic schemas (includes slug in response)
│   ├── routes/
│   │   └── community_routes.py # All community endpoints
│   └── core/
│       ├── config.py, security.py, dependencies.py
│       ├── permissions.py, exceptions.py
└── logs/
    └── community_service.log
```

---

## Interview Q&A

**Q: Why use slugs instead of IDs in URLs?**
A: Slugs are human-readable and SEO-friendly. `/communities/python-developers` tells you what the page is about, while `/communities/5` means nothing. It also prevents enumeration attacks (guessing sequential IDs).

**Q: How do you handle slug uniqueness?**
A: On creation, we generate a slug from the name. If it already exists, we append `-2`, `-3`, etc. When a community is renamed, the slug is regenerated. The slug column has a unique database constraint as the final safety net.
