# 08 — Frontend (React, Port 3000)

## What Does the Frontend Do?

**Simple analogy:** The frontend is the "face" of the app — everything you see and click. It talks to the backend gateway via API calls and receives real-time updates via WebSocket.

**In interview terms:** A single-page application (SPA) built with React 19, Material UI 7, and React Router v6. Authentication uses httpOnly cookies (no tokens in JavaScript). Real-time features use WebSocket with auto-reconnect and exponential backoff.

---

## Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| React | 19 | UI framework |
| Material UI (MUI) | 7 | Component library + theming |
| React Router | 6 | Client-side routing |
| Axios | 1.14 | HTTP client with cookie support |
| Emotion | 11 | CSS-in-JS (used by MUI) |

---

## Pages (15 total)

| Page | Route | Description |
|------|-------|-------------|
| Login | `/login` | Email + password login form |
| Register | `/register` | New account registration |
| ForgotPassword | `/forgot-password` | Send password reset email |
| ResetPassword | `/reset-password` | Set new password via email token |
| Home | `/` | Feed of all threads (paginated) |
| CreateThread | `/threads/new` | Create a new thread (community selector) |
| ThreadDetail | `/threads/:id` | View thread + nested comments + likes |
| Communities | `/communities` | List of all communities (join/leave) |
| CommunityDetail | `/communities/:slug` | Community threads + member list |
| Profile | `/profile` | View/edit profile + avatar upload |
| Notifications | `/notifications` | Full notification history (mark read) |
| Dashboard | `/dashboard` | Role-based: Admin, Moderator, or Member |
| AdminPanel | (inside Dashboard) | User management (roles, activate/deactivate/delete) |
| ModeratorPanel | (inside Dashboard) | View/manage reported threads |
| MemberDashboard | (inside Dashboard) | User's threads, comments, communities |

---

## Authentication Flow (Cookie-Based)

```
Login:
1. User submits email + password
2. Frontend POSTs to /auth/login (form data, withCredentials: true)
3. Gateway proxies to user_service, gets JWT
4. Gateway sets httpOnly cookie + returns user data (no token in body)
5. Frontend calls login() → sets isLoggedIn=true (no token stored in JS)

Page Refresh:
1. On mount, AuthContext calls GET /auth/me (cookie sent automatically)
2. If 200 → user is logged in, populate user state
3. If 401 → redirect to login

Logout:
1. Frontend POSTs to /auth/logout
2. Gateway blacklists token in Redis + deletes cookie
3. Frontend clears local state
```

**Key point:** No token is ever stored in JavaScript (no `localStorage`, no `sessionStorage`). The httpOnly cookie is managed entirely by the browser and gateway.

---

## API Layer (`api/api.js`)

```javascript
const api = axios.create({
    baseURL: 'http://localhost:8000',   // Talk to gateway
    withCredentials: true,               // Send/receive httpOnly cookies
});
```

**401 Interceptor:** If any API call returns 401 and the user thinks they're logged in, it triggers a force logout (handles deleted/deactivated accounts or expired tokens).

**No manual headers:** Unlike traditional SPAs, there's no `Authorization: Bearer <token>` header. The cookie is sent automatically by the browser.

---

## AuthContext (Global State)

The `AuthContext` provides these values to the entire app:

| Value | Type | Description |
|-------|------|-------------|
| `isLoggedIn` | boolean | Whether user has an active session |
| `token` | boolean | Alias for `isLoggedIn` (backward compat) |
| `user` | object | Current user data (`{id, username, email, role, avatar, ...}`) |
| `notification` | object | Latest real-time notification (for popup) |
| `unreadCount` | number | Badge count for notification bell |
| `broadcastEvent` | object | Latest broadcast event (for live UI updates) |
| `login()` | function | Mark as logged in (no arguments — cookie is set by gateway) |
| `logout()` | function | POST `/auth/logout` + clear state |
| `refreshUnreadCount()` | function | Manually refresh notification count |

**Initialization:** On mount, calls `/auth/me` to check cookie validity. Shows nothing (loading) until the check completes, preventing a flash of the login page.

---

## WebSocket (Real-Time Notifications)

```
Connection: ws://localhost:8007/ws
Auth: Cookie sent automatically by browser with WS upgrade request
Reconnect: Auto-reconnect with exponential backoff (1s → 2s → 4s → ... → 30s max)
```

**Event handling in AuthContext:**

| Event Type | What Happens |
|------------|-------------|
| `ping` | Ignored (keepalive) |
| `account_deleted` / `account_deactivated` | Shows message, auto-logout in 3 seconds |
| `account_activated` | Shows notification popup |
| `role_change` | Refreshes user profile (role updates live) |
| `avatar_update` | Refreshes user profile if it's the current user |
| Broadcast events (likes, new threads, etc.) | Sets `broadcastEvent` state for live UI updates |
| Personal notifications | Shows popup, refreshes unread count, auto-clears after 6s |
| Self-actions | Skips popup (you don't need "You liked a thread" notifications) |

---

## Theme System (Dark/Light Mode)

Two themes available, toggled with a button in the Navbar:

| Property | Dark Mode | Light Mode |
|----------|-----------|------------|
| Background | `#030303` (near black) | `#DAE0E6` (light gray) |
| Paper | `#1A1A1B` | `#FFFFFF` |
| Primary | `#7C4DFF` (purple) | `#7C4DFF` (purple) |
| Secondary | `#00E5FF` (cyan) | `#0097A7` (teal) |

Theme preference is saved in `localStorage('themeMode')` — this is the only thing stored in localStorage.

---

## Routing & Protection

All routes except login/register/forgot-password/reset-password require authentication:

```jsx
<Route path="/" element={token ? <Home /> : <Navigate to="/login" />} />
```

If logged in and visiting `/login`, you're redirected to `/`. If not logged in and visiting `/`, you're redirected to `/login`.

Community pages use slugs: `/communities/python-developers` instead of `/communities/5`.

---

## Key Components

| Component | Purpose |
|-----------|---------|
| `Navbar` | Top bar with logo, search, notification bell (badge), theme toggle, user menu |
| `UserAvatar` | Reusable avatar component with fallback initials |
| `ConfirmDialog` | Reusable confirmation modal (delete, leave, etc.) |

---

## File Structure

```
frontend/src/
├── App.js               # Routes + auth guards
├── index.js             # Entry point (AuthProvider + ThemeProvider)
├── theme.js             # Dark/light theme config
├── api/
│   └── api.js           # Axios instance + 401 interceptor
├── context/
│   ├── AuthContext.js   # Auth state, WebSocket, notifications
│   └── ThemeContext.js  # Dark/light mode toggle
├── components/
│   ├── Navbar.js        # Top navigation bar
│   ├── UserAvatar.js    # Avatar with fallback
│   └── ConfirmDialog.js # Confirmation modal
├── pages/
│   ├── Login.js, Register.js, ForgotPassword.js, ResetPassword.js
│   ├── Home.js, CreateThread.js, ThreadDetail.js
│   ├── Communities.js, CommunityDetail.js
│   ├── Profile.js, Notifications.js
│   ├── Dashboard.js, AdminPanel.js, ModeratorPanel.js, MemberDashboard.js
└── utils/
    ├── displayUser.js   # Format username for display
    └── timeAgo.js       # "2 hours ago" time formatting
```

---

## Interview Q&A

**Q: Why use httpOnly cookies instead of localStorage for JWT?**
A: httpOnly cookies can't be read by JavaScript, making them immune to XSS attacks. With localStorage, any XSS vulnerability could steal the token. The cookie approach is more secure with zero extra code on the frontend — the browser handles it automatically.

**Q: How does the app know if the user is logged in on page refresh?**
A: On mount, `AuthContext` makes a `GET /auth/me` call. The browser automatically sends the httpOnly cookie. If the server returns 200, the user is logged in. If 401, the session has expired.

**Q: How does live update work for likes and new threads?**
A: The backend publishes events to Kafka. The notification service consumes them and broadcasts via WebSocket to all connected clients. The frontend's `AuthContext` sets a `broadcastEvent` state, and individual pages (like `ThreadDetail`) listen for changes and update the UI without a page refresh.

**Q: What happens if the WebSocket disconnects?**
A: Auto-reconnect with exponential backoff — starts at 1 second, doubles each time, caps at 30 seconds. On successful reconnect, the delay resets. This handles network blips gracefully.
