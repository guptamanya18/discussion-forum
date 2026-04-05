# 10 — Flow Diagrams

Visual walkthroughs of major operations in the system.

---

## 1. User Login Flow

```
┌──────────┐     POST /auth/login      ┌──────────┐    proxy     ┌──────────────┐
│ Frontend │ ─────────────────────────► │ Gateway  │ ──────────► │ User Service │
│ (React)  │   email + password         │ (8000)   │             │   (8001)     │
└──────────┘   withCredentials: true    └──────────┘             └──────────────┘
                                             │                         │
                                             │    ◄────────────────────┘
                                             │    { access_token, user }
                                             │
                                       ┌─────▼─────┐
                                       │  Gateway   │
                                       │ processes: │
                                       │ 1. Set     │
                                       │  httpOnly  │
                                       │  cookie    │
                                       │ 2. Strip   │
                                       │  token     │
                                       │  from body │
                                       └─────┬─────┘
                                             │
                                             ▼
                                       ┌──────────┐
                                       │ Frontend  │
                                       │ receives: │
                                       │ { user }  │
                                       │ (no token)│
                                       │           │
                                       │ Sets:     │
                                       │ isLoggedIn│
                                       │ = true    │
                                       └──────────┘
```

---

## 2. Authenticated Request Flow

```
┌──────────┐   GET /threads            ┌──────────┐              ┌────────────────┐
│ Frontend │ ──────────────────────────►│ Gateway  │─────────────►│ Thread Service │
│          │  (cookie sent by browser)  │          │  + injects   │    (8002)      │
└──────────┘                            │          │  Authorization│               │
                                        │ Steps:   │  Bearer      │               │
                                        │ 1. Read  │  header      │               │
                                        │  cookie  │              │               │
                                        │ 2. Check │              │               │
                                        │  blacklist│             │               │
                                        │  (Redis) │              │               │
                                        │ 3. Check │              │               │
                                        │  rate    │              │               │
                                        │  limit   │              │               │
                                        │ 4. Inject│              │               │
                                        │  header  │              │               │
                                        │ 5. Proxy │──────────────►               │
                                        └──────────┘              └────────────────┘
```

---

## 3. Thread Creation Flow

```
┌──────────┐     POST /threads          ┌──────────┐              ┌────────────────┐
│ Frontend │ ──────────────────────────► │ Gateway  │ ───────────► │ Thread Service │
│          │  { title, description,      │          │              │                │
│          │    tags, community_id }     │          │              │  1. Validate   │
└──────────┘                             └──────────┘              │     input      │
                                                                   │  2. Create     │
                                                                   │     thread     │
                                                                   │     in DB      │
                                                                   │  3. Publish    │
                                                                   │     Kafka      │
                                                                   │     event      │
                                                                   └───────┬────────┘
                                                                           │
                                                          Kafka: thread-events
                                                          { type: "new_thread",
                                                            broadcast: true,
                                                            thread: {...} }
                                                                           │
                                                                           ▼
                                                                  ┌────────────────────┐
                                                                  │ Notification Svc   │
                                                                  │  Kafka Consumer    │
                                                                  │                    │
                                                                  │ broadcast=true →   │
                                                                  │ WebSocket.broadcast│
                                                                  │ to ALL clients     │
                                                                  └────────────────────┘
                                                                           │
                                                                      WebSocket
                                                                           │
                                                                           ▼
                                                                   ┌──────────────┐
                                                                   │ All Clients  │
                                                                   │ see new      │
                                                                   │ thread live  │
                                                                   └──────────────┘
```

---

## 4. Comment + Notification Flow

```
User A posts a comment on User B's thread:

┌──────────┐  POST /comments            ┌──────────┐  proxy   ┌─────────────────┐
│ User A   │ ──────────────────────────► │ Gateway  │ ───────► │ Comment Service │
│ Frontend │  { content, thread_id }     │          │          │                 │
└──────────┘                             └──────────┘          │ 1. Save comment │
                                                               │ 2. GET thread   │
                                                               │    from thread  │
                                                               │    service (to  │
                                                               │    find owner)  │
                                                               │ 3. Publish      │
                                                               │    Kafka events │
                                                               └────────┬────────┘
                                                                        │
                                                         ┌──────────────┼──────────────┐
                                                         │              │              │
                                                    Broadcast      Targeted      Broadcast
                                                    Event          Notification   Event
                                                    (new comment)  (to thread     (if reply,
                                                                    owner B)      to parent
                                                                                  author)
                                                         │              │              │
                                                         ▼              ▼              ▼
                                                   ┌─────────────────────────────────────┐
                                                   │      Notification Service           │
                                                   │                                     │
                                                   │  Broadcast → WebSocket.broadcast()  │
                                                   │  Targeted → Save to DB +            │
                                                   │             WebSocket.send_to_user() │
                                                   └─────────────────────────────────────┘
                                                              │              │
                                                              ▼              ▼
                                                   ┌──────────┐    ┌──────────┐
                                                   │ All users │    │ User B   │
                                                   │ see new   │    │ gets     │
                                                   │ comment   │    │ bell     │
                                                   │ appear    │    │ notif    │
                                                   └──────────┘    └──────────┘
```

---

## 5. Like Toggle Flow

```
┌──────────┐  POST /threads/5/like      ┌──────────┐         ┌────────────────┐
│ User     │ ──────────────────────────► │ Gateway  │ ──────► │ Thread Service │
└──────────┘                             └──────────┘         │                │
                                                              │  Check: does   │
                                                              │  Like row      │
                                                              │  exist?        │
                                                              │                │
                                                              │  No  → INSERT  │
                                                              │        (liked) │
                                                              │  Yes → DELETE  │
                                                              │      (unliked)│
                                                              │                │
                                                              │  Count total   │
                                                              │  likes         │
                                                              │                │
                                                              │  Publish Kafka │
                                                              │  broadcast:    │
                                                              │  { thread_id,  │
                                                              │    like_count }│
                                                              └───────┬────────┘
                                                                      │
                                                                 Kafka event
                                                                      │
                                                                      ▼
                                                             ┌────────────────┐
                                                             │ Notification   │
                                                             │ Service        │
                                                             │ broadcasts to  │
                                                             │ all clients    │
                                                             └────────────────┘
                                                                      │
                                                                 WebSocket
                                                                      │
                                                                      ▼
                                                              ┌──────────────┐
                                                              │ All clients  │
                                                              │ update like  │
                                                              │ counter      │
                                                              │ instantly    │
                                                              └──────────────┘
```

---

## 6. Logout Flow

```
┌──────────┐   POST /auth/logout        ┌──────────┐
│ Frontend │ ──────────────────────────► │ Gateway  │
│          │  (cookie sent by browser)   │          │
└──────────┘                             │  Steps:  │
                                         │  1. Read │
                                         │   token  │
                                         │   from   │
                                         │   cookie │
                                         │  2. Add  │
                                         │   token  │
                                         │   to     │
                                         │   Redis  │
                                         │   black- │
                                         │   list   │
                                         │  3. Del  │
                                         │   cookie │
                                         │  4. Return│
                                         │   200    │
                                         └────┬─────┘
                                              │
                                              ▼
                                         ┌──────────┐
                                         │ Frontend │
                                         │ clears:  │
                                         │ isLoggedIn│
                                         │ = false  │
                                         │ user=null│
                                         │ close WS │
                                         └──────────┘
```

---

## 7. Admin Delete User Flow

```
┌───────────┐  DELETE /users/42          ┌──────────┐         ┌──────────────┐
│ Admin     │ ──────────────────────────►│ Gateway  │────────►│ User Service │
│ Frontend  │                            └──────────┘         │              │
└───────────┘                                                 │ 1. Soft-delete│
                                                              │    user      │
                                                              │    (set      │
                                                              │   deleted_at)│
                                                              │ 2. Publish   │
                                                              │   Kafka:     │
                                                              │ user-events  │
                                                              │ {type:       │
                                                              │ account_     │
                                                              │ deleted}     │
                                                              └──────┬───────┘
                                                                     │
                                                                Kafka event
                                                                     │
                                                                     ▼
                                                             ┌───────────────┐
                                                             │ Notification  │
                                                             │ Service       │
                                                             │               │
                                                             │ send_to_user  │
                                                             │ (42, {type:   │
                                                             │ account_      │
                                                             │ deleted})     │
                                                             └───────┬───────┘
                                                                     │
                                                                WebSocket
                                                                     │
                                                                     ▼
                                                              ┌──────────┐
                                                              │ User 42  │
                                                              │ sees:    │
                                                              │ "Account │
                                                              │ deleted. │
                                                              │ Logging  │
                                                              │ out in   │
                                                              │ 3s..."   │
                                                              │          │
                                                              │ Auto     │
                                                              │ logout   │
                                                              └──────────┘
```

---

## 8. Keyword Search Flow

```
┌──────────┐   GET /threads?search=     ┌──────────┐         ┌────────────────┐
│ Frontend │   python async             │ Gateway  │────────►│ Thread Service │
│ Navbar   │ ──────────────────────────►│          │         │                │
│ search   │                            └──────────┘         │ 1. Split query │
│ bar      │                                                 │    "python     │
└──────────┘                                                 │     async"     │
                                                             │    → ["python",│
                                                             │       "async"] │
                                                             │                │
                                                             │ 2. For each    │
                                                             │    word, add   │
                                                             │    AND filter: │
                                                             │    title ILIKE │
                                                             │    %python%    │
                                                             │    OR desc     │
                                                             │    ILIKE       │
                                                             │    %python%    │
                                                             │    OR tags     │
                                                             │    contain     │
                                                             │    "python"    │
                                                             │                │
                                                             │ 3. Return      │
                                                             │    matching    │
                                                             │    threads     │
                                                             └────────────────┘
```

---

## 9. Password Reset Flow

```
Step 1: Request reset email

┌──────────┐  POST /auth/forgot-password  ┌──────────┐      ┌──────────────┐     ┌─────────┐
│ Frontend │  { email }                    │ Gateway  │─────►│ User Service │────►│ Mailpit │
└──────────┘ ─────────────────────────────►└──────────┘      │              │     │ (SMTP)  │
                                                             │ 1. Find user │     │         │
                                                             │ 2. Generate  │     │ Sends   │
                                                             │    reset     │     │ email   │
                                                             │    token     │     │ with    │
                                                             │ 3. Send      │────►│ link    │
                                                             │    email     │     │         │
                                                             └──────────────┘     └─────────┘

Step 2: Reset password

┌──────────┐  POST /auth/reset-password   ┌──────────┐      ┌──────────────┐
│ Frontend │  { token, new_password }      │ Gateway  │─────►│ User Service │
└──────────┘ ─────────────────────────────►└──────────┘      │              │
                                                             │ 1. Verify    │
                                                             │    token     │
                                                             │ 2. Hash new  │
                                                             │    password  │
                                                             │ 3. Update    │
                                                             │    user      │
                                                             └──────────────┘
```
