# 03 — User & Auth Service (Port 8002)

## What Does This Service Do?

**Simple analogy:** This is the "front desk" of the forum. It handles everything related to people: who they are, how they log in, what role they have, and their profile settings.

**In interview terms:** The User & Auth Service is responsible for user registration, authentication (login/logout), profile management, avatar uploads, password reset flow, and admin user management. It uses JWT tokens for stateless auth, bcrypt for password hashing, and publishes events to Kafka for real-time notifications.

---

## Database: `user_db`

**Table: `users`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-incrementing user ID |
| `username` | String (unique) | Login name, alphanumeric + underscore, min 3 chars |
| `email` | String (unique) | Email address for password reset |
| `hashed_password` | String | bcrypt hash (never stored in plain text) |
| `role` | String | `member`, `moderator`, `admin`, or `deleted` |
| `name` | String (nullable) | Display name |
| `bio` | String (nullable) | User bio |
| `avatar` | String (nullable) | Path to avatar image (e.g., `/uploads/avatars/1_abc.jpg`) |
| `is_active` | Integer | 1 = active, 0 = deactivated by admin |
| `created_at` | DateTime | Registration timestamp |
| `deleted_at` | DateTime (nullable) | Soft-delete timestamp (NULL = not deleted) |

---

## Authentication: How Login Works

```
1. User sends: POST /auth/login { username, password }
2. Service looks up user by username in the database
3. Verifies password using bcrypt (compare hash)
4. If match → creates a JWT token with payload { sub: "user_id", exp: now+90min }
5. Returns { access_token: "eyJ...", token_type: "bearer" }
6. Gateway intercepts this response, sets the token as an httpOnly cookie, and strips it from the body
```

**JWT Token Structure (decoded):**
```json
{
  "sub": "1",          // user ID as string
  "exp": 1712188800   // expiry timestamp (90 minutes from creation)
}
```

**Protected Routes:** Every request to a protected endpoint includes the token via cookie → gateway injects `Authorization: Bearer <token>` → service extracts it using FastAPI's `HTTPBearer()` dependency → decodes and looks up the user.

---

## Password Security

- **Hashing:** bcrypt (from `passlib`) — deliberately slow to resist brute-force
- **Validation rules:** Min 5 chars, at least 1 letter, at least 1 number
- **Password Reset:** Email-based flow using a short-lived JWT (15-minute expiry) with `purpose: "reset"`

```
Forgot Password Flow:
1. User enters email → POST /auth/forgot-password
2. Service finds user by email
3. Creates a reset token (JWT, 15-min expiry)
4. Sends email via SMTP (Mailpit in dev) with link: http://localhost:3000/reset-password?token=xxx
5. User clicks link → enters new password → POST /auth/reset-password { token, new_password }
6. Service verifies token, hashes new password, updates DB
```

**Anti-enumeration:** The forgot-password endpoint always returns the same message whether the email exists or not, preventing attackers from discovering which emails are registered.

---

## API Endpoints

### Auth Routes (prefix: `/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | No | Login with username + password (form data) |
| GET | `/auth/me` | Yes | Get current user's profile |
| POST | `/auth/forgot-password` | No | Send password reset email |
| POST | `/auth/reset-password` | No | Reset password with token |

### User Routes (prefix: `/users`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/users/register` | No | Create new user account |
| PUT | `/users/profile` | Yes | Update own name/bio/avatar |
| POST | `/users/avatar/upload` | Yes | Upload avatar image (multipart) |
| GET | `/users/{user_id}` | Yes | Get any user's public profile |
| GET | `/users/me/dashboard` | Yes | Get own dashboard data |

### Admin Routes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/users/admin/stats` | Admin | Platform-wide user stats |
| GET | `/users/admin/users` | Admin | List all users (with search/filter) |
| PUT | `/users/{user_id}` | Admin | Change a user's role |
| POST | `/users/admin/users/{id}/status` | Admin | Activate or deactivate a user |
| DELETE | `/users/admin/users/{id}` | Admin | Soft-delete a user |

### Moderator Routes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/users/mod/users` | Mod+ | List users (paginated, searchable) |
| GET | `/users/mod/stats` | Mod+ | User stats + recent registrations |

---

## Avatar Upload

- **Endpoint:** POST `/users/avatar/upload` (multipart form)
- **Allowed types:** `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- **Max size:** 5 MB
- **Storage:** `/app/uploads/avatars/{userId}_{uuid}.{ext}` inside the container
- **Serving:** FastAPI `StaticFiles` mount at `/uploads`
- **Cleanup:** Old avatar file is deleted when a new one is uploaded
- **Kafka event:** `avatar_update` is broadcast so all connected clients see the new avatar

---

## Admin User Management

### Activate/Deactivate (soft disable)
- Sets `is_active` to 0 (deactivated) or 1 (activated)
- Deactivated users **cannot log in** — the `get_current_user` dependency checks `is_active`
- User's content (threads, comments) remains visible
- Admin receives instant feedback; the target user gets a WebSocket notification and is **force-logged-out in 3 seconds**

### Delete User (soft delete)
- Sets `deleted_at` to current timestamp
- Username changed to `[deleted_N]`, email to `deleted_N@deleted.local`
- Password and role cleared
- Content remains but shows the anonymized username
- Target user gets force-logged-out via WebSocket

**Why soft delete?** Hard-deleting a user would break all their threads and comments (foreign key issues). Soft delete preserves content integrity.

---

## Kafka Events Published

| Event Type | Topic | When |
|------------|-------|------|
| `avatar_update` | `user-events` | User uploads new avatar |
| `account_deactivated` | Via HTTP to notification service | Admin deactivates user |
| `account_activated` | Via HTTP to notification service | Admin activates user |
| `account_deleted` | Via HTTP to notification service | Admin deletes user |
| `role_change` | Via HTTP to notification service | Admin changes user role |

---

## File Structure

```
backend/services/user_service/
├── app/
│   ├── main.py              # Lifespan, bootstrap admin, DB migration
│   ├── database.py          # Async SQLAlchemy engine + session
│   ├── kafka_producer.py    # AIOKafka producer (sends events)
│   ├── models/
│   │   └── user.py          # SQLAlchemy User model
│   ├── schemas/
│   │   └── user.py          # Pydantic validation schemas
│   ├── routes/
│   │   ├── auth_routes.py   # Login, /me, forgot/reset password
│   │   └── user_routes.py   # Register, profile, avatar, admin CRUD
│   ├── services/
│   │   ├── auth_service.py  # authenticate_user() — bcrypt verify
│   │   └── user_service.py  # create_user() — registration logic
│   └── core/
│       ├── config.py        # Pydantic settings (DB URL, secret, SMTP)
│       ├── security.py      # JWT creation, bcrypt hash/verify
│       ├── dependencies.py  # get_current_user() — JWT → User lookup
│       ├── permissions.py   # ensure_role(), validate_role()
│       ├── exceptions.py    # Custom exceptions (404, 401, 400, 409)
│       └── email.py         # SMTP email sending (password reset)
├── tests/
│   ├── conftest.py          # Test fixtures (in-memory SQLite DB)
│   └── test_users.py        # Registration + login tests
└── logs/
    └── user_service.log
```

---

## Interview Q&A

**Q: How do you handle password storage?**
A: We never store plain-text passwords. We use bcrypt (via passlib) which is a one-way hash. During login, we hash the submitted password and compare it with the stored hash. bcrypt is deliberately slow (~100ms per hash) which makes brute-force attacks impractical.

**Q: What happens when an admin deletes a user?**
A: It's a soft delete — we set `deleted_at`, anonymize the username to `[deleted_N]`, and clear the password. The user's threads and comments remain visible with the anonymized name. The user receives a WebSocket notification and is force-logged-out after 3 seconds.

**Q: Why use a bootstrap admin?**
A: On first boot, there are no users in the database. The service automatically creates an admin account (`alice/pass123`) so you can immediately log in and manage the platform. It checks if the admin already exists before creating, so it's idempotent.
