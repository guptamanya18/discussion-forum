"""
Seed script – populates the Discussion Forum with sample data via the API gateway.
Run:  pip install httpx   (once)
      python seed_data.py
"""

import httpx, random, time, sys

BASE = "http://localhost:8000"
PASSWORD = "pass123"

client = httpx.Client(base_url=BASE, timeout=15)


# ── Wait for gateway + all services to be ready ─────────────────────────────
def wait_for_services(max_wait=120):
    """Poll the gateway until it responds, up to max_wait seconds."""
    print("\n⏳ Waiting for services to be ready...")
    start = time.time()
    while time.time() - start < max_wait:
        try:
            r = client.get("/health")
            if r.status_code == 200:
                print("  ✔ Gateway is ready!\n")
                return
        except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError):
            pass
        # Also try a lightweight endpoint as fallback
        try:
            r = client.get("/communities?limit=1")
            if r.status_code in (200, 401):
                print("  ✔ Services are ready!\n")
                return
        except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError):
            pass
        time.sleep(3)
        elapsed = int(time.time() - start)
        print(f"  … still waiting ({elapsed}s)")
    print("  ✗ Services did not become ready in time. Exiting.")
    sys.exit(1)

wait_for_services()


# ── helpers ──────────────────────────────────────────────────────────────────
def register(username, email, password):
    for attempt in range(3):
        try:
            r = client.post("/users/register", json={"username": username, "email": email, "password": password})
            break
        except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError):
            time.sleep(2)
    else:
        print(f"  ✗ Could not reach server for {username}")
        return None
    if r.status_code == 200:
        print(f"  ✔ Registered: {username}")
        return r.json()
    print(f"  – Skip {username}: already exists")
    return None


def login(username, password):
    for _ in range(5):  # Retry up to 5 times
        try:
            r = client.post("/auth/login", data={"username": username, "password": password},
                            headers={"Content-Type": "application/x-www-form-urlencoded"})
            if r.status_code == 200:
                # Token is in httpOnly cookie (set by gateway), or in response body (direct API)
                token = r.cookies.get("access_token") or r.json().get("access_token")
                if token:
                    return token
                print(f"  ✗ No token received for {username}")
                return None
            if r.status_code == 429:
                print(f"  ! Rate limited for {username}, retrying in 3s...")
                time.sleep(3)
                continue
            print(f"  ✗ Login failed for {username}: {r.text}")
            return None
        except httpx.RequestError as exc:
            print(f"  ! Request error {exc}, retrying...")
            time.sleep(1)
    return None


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── 1. Create 10 users ──────────────────────────────────────────────────────
print("\n=== Creating Users ===")
users = [
    {"username": "alice",    "email": "alice@example.com",    "role": "admin"},
    {"username": "bob",      "email": "bob@example.com",      "role": "moderator"},
    {"username": "charlie",  "email": "charlie@example.com",  "role": "member"},
    {"username": "diana",    "email": "diana@example.com",    "role": "member"},
    {"username": "eve",      "email": "eve@example.com",      "role": "member"},
    {"username": "frank",    "email": "frank@example.com",    "role": "member"},
    {"username": "grace",    "email": "grace@example.com",    "role": "member"},
    {"username": "henry",    "email": "henry@example.com",    "role": "member"},
    {"username": "ivy",      "email": "ivy@example.com",      "role": "member"},
    {"username": "jack",     "email": "jack@example.com",     "role": "member"},
    {"username": "karen",    "email": "karen@example.com",    "role": "member"},
    {"username": "leo",      "email": "leo@example.com",      "role": "member"},
    {"username": "mia",      "email": "mia@example.com",      "role": "member"},
    {"username": "noah",     "email": "noah@example.com",     "role": "member"},
    {"username": "olivia",   "email": "olivia@example.com",   "role": "member"},
    {"username": "peter",    "email": "peter@example.com",    "role": "member"},
    {"username": "quinn",    "email": "quinn@example.com",    "role": "member"},
    {"username": "rachel",   "email": "rachel@example.com",   "role": "member"},
    {"username": "sam",      "email": "sam@example.com",      "role": "member"},
    {"username": "tina",     "email": "tina@example.com",     "role": "member"},
]

for u in users:
    register(u["username"], u["email"], PASSWORD)
    time.sleep(0.3)

# Let services finish processing registrations + Kafka events
print("\n  ⏳ Waiting for services to settle...")
time.sleep(5)

print("\n=== Logging In ===")
tokens = {}
for u in users:
    t = login(u["username"], PASSWORD)
    if t:
        tokens[u["username"]] = t
        print(f"  ✔ Logged in: {u['username']}")
    time.sleep(0.5)

usernames = list(tokens.keys())

# Promote roles via admin
admin_token = tokens.get("alice")
if admin_token:
    for u in users:
        if u["role"] != "member":
            r = client.get("/users/admin/users", headers=auth(admin_token))
    # Promote bob to moderator
    bob_info = client.get("/auth/me", headers=auth(tokens.get("bob", ""))).json()
    if bob_info and bob_info.get("role") != "moderator":
        r = client.put(f"/users/{bob_info['id']}", json={"role": "moderator"}, headers=auth(admin_token))
        if r.status_code == 200:
            print("  ✔ bob promoted to moderator")

# ── 2. Create 5 communities ─────────────────────────────────────────────────
print("\n=== Creating Communities ===")
community_data = [
    {"name": "Python Developers",    "description": "Everything Python — from basics to advanced async patterns."},
    {"name": "Web Dev Hub",          "description": "Frontend, backend, and full-stack web development discussions."},
    {"name": "Data Science Lab",     "description": "Machine learning, AI, data engineering, and analytics."},
    {"name": "DevOps Corner",        "description": "CI/CD, Docker, Kubernetes, and infrastructure as code."},
    {"name": "Open Source Cafe",     "description": "Contributing to open source, licensing, and community building."},
    {"name": "Mobile App Builders",  "description": "React Native, Flutter, Swift, Kotlin — mobile dev discussions."},
    {"name": "Cloud Architecture",   "description": "AWS, GCP, Azure — cloud patterns and best practices."},
    {"name": "Cybersecurity Hub",    "description": "Security, ethical hacking, penetration testing, and compliance."},
]

creators = ["alice", "bob", "charlie", "diana", "eve", "frank", "grace", "henry"]
community_ids = []
for i, c in enumerate(community_data):
    creator = creators[i]
    r = client.post("/communities", json=c, headers=auth(tokens[creator]))
    if r.status_code == 200:
        cid = r.json()["id"]
        community_ids.append(cid)
        print(f"  ✔ Created: {c['name']} (id={cid}) by {creator}")
    else:
        print(f"  – Skip: {c['name']}")

# ── 3. Join communities (each community gets 5-8 members) ───────────────────
print("\n=== Joining Communities ===")
for cid in community_ids:
    joiners = random.sample(usernames, k=random.randint(8, min(14, len(usernames))))
    for name in joiners:
        r = client.post(f"/communities/{cid}/join", headers=auth(tokens[name]))
        if r.status_code == 200:
            print(f"  ✔ {name} joined community {cid}")

# ── 4. Create 10 threads ────────────────────────────────────────────────────
print("\n=== Creating Threads ===")
thread_data = [
    {"title": "Best practices for async Python",
     "description": "What are your go-to patterns for writing clean async code? Share tips, libraries, and pitfalls to avoid.",
     "tags": ["python", "async", "best-practices"]},
    {"title": "React vs Vue vs Svelte in 2026",
     "description": "With all three frameworks maturing, which do you pick for new projects? Performance, DX, ecosystem.",
     "tags": ["react", "vue", "svelte", "frontend"]},
    {"title": "Getting started with Docker Compose",
     "description": "A beginner-friendly thread on multi-container setups. Share your docker-compose.yml patterns!",
     "tags": ["docker", "devops", "microservices"]},
    {"title": "FastAPI advanced patterns",
     "description": "Dependency injection, background tasks, middleware, WebSockets — share production FastAPI setups.",
     "tags": ["python", "fastapi", "backend"]},
    {"title": "Machine Learning project ideas for 2026",
     "description": "Looking for portfolio-worthy ML projects. What interesting datasets or problems have you tackled?",
     "tags": ["machine-learning", "portfolio", "ai"]},
    {"title": "PostgreSQL performance tuning",
     "description": "Indexes, query plans, connection pooling, partitioning — share your optimization tips.",
     "tags": ["postgresql", "database", "performance"]},
    {"title": "Microservices vs Monolith debate",
     "description": "When should you go microservices? Share real-world experiences, failures, and lessons learned.",
     "tags": ["architecture", "microservices", "monolith"]},
    {"title": "TypeScript tips you wish you knew earlier",
     "description": "Utility types, branded types, discriminated unions — what features changed your workflow?",
     "tags": ["typescript", "javascript", "tips"]},
    {"title": "Building real-time apps with WebSockets",
     "description": "Chat apps, live dashboards, notifications — how do you handle WebSocket connections at scale?",
     "tags": ["websocket", "real-time", "backend"]},
    {"title": "Open source contribution guide",
     "description": "How to find your first issue, write a good PR, and navigate large codebases.",
     "tags": ["open-source", "git", "community"]},
    {"title": "Kubernetes for beginners",
     "description": "Pods, services, deployments, configmaps — getting started with K8s from scratch.",
     "tags": ["kubernetes", "devops", "containers"]},
    {"title": "GraphQL vs REST in 2026",
     "description": "Is GraphQL worth the complexity? When does REST still win? Real-world trade-offs.",
     "tags": ["graphql", "rest", "api-design"]},
    {"title": "How to ace system design interviews",
     "description": "Load balancers, caching, sharding, message queues — share your study strategies and resources.",
     "tags": ["system-design", "interviews", "career"]},
    {"title": "Rust for Python developers",
     "description": "Making the jump from Python to Rust. What concepts transfer and what is completely new?",
     "tags": ["rust", "python", "programming"]},
    {"title": "CI/CD pipeline best practices",
     "description": "GitHub Actions, Jenkins, GitLab CI — share your battle-tested pipeline configurations.",
     "tags": ["ci-cd", "automation", "devops"]},
    {"title": "Database migration strategies",
     "description": "Alembic, Flyway, zero-downtime migrations — how do you handle schema changes in production?",
     "tags": ["database", "migrations", "backend"]},
    {"title": "Authentication patterns in microservices",
     "description": "JWT, OAuth2, API keys, service mesh — securing inter-service communication.",
     "tags": ["authentication", "security", "microservices"]},
    {"title": "Frontend state management in 2026",
     "description": "Redux, Zustand, Jotai, Signals — which state management solution do you prefer and why?",
     "tags": ["frontend", "state-management", "react"]},
    {"title": "Monitoring and observability stack",
     "description": "Prometheus, Grafana, ELK, Jaeger — how do you monitor your services in production?",
     "tags": ["monitoring", "observability", "devops"]},
    {"title": "Building a design system from scratch",
     "description": "Component libraries, tokens, accessibility — share your experience building design systems.",
     "tags": ["design-system", "ui-ux", "frontend"]},
]

thread_ids = []
thread_authors = []
for i, t in enumerate(thread_data):
    creator = usernames[i % len(usernames)]
    body = {**t}
    if community_ids:
        body["community_id"] = community_ids[i % len(community_ids)]
    r = client.post("/threads", json=body, headers=auth(tokens[creator]))
    if r.status_code == 200:
        tid = r.json()["id"]
        thread_ids.append(tid)
        thread_authors.append(creator)
        print(f"  ✔ \"{t['title'][:45]}\" (id={tid}) by {creator}")
    else:
        print(f"  ✗ Failed: {t['title'][:30]} — {r.text[:80]}")

# ── 5. Like threads (each thread gets 2-5 likes) ────────────────────────────
print("\n=== Liking Threads ===")
for tid in thread_ids:
    likers = random.sample(usernames, k=random.randint(3, min(8, len(usernames))))
    for name in likers:
        r = client.post(f"/threads/{tid}/like", headers=auth(tokens[name]))
        if r.status_code == 200:
            data = r.json()
            if data.get("liked"):
                print(f"  ✔ {name} liked thread {tid}")

# ── 6. Create comments (3-5 per thread = ~40 comments) ──────────────────────
print("\n=== Creating Comments ===")
comment_ids = []
comments_pool = [
    "Great point! I totally agree with this approach.",
    "Interesting perspective. Have you considered the trade-offs with scalability?",
    "Thanks for sharing! This saved me hours of debugging.",
    "I had a similar experience. Here's what worked for me in production.",
    "Can you elaborate more on this? I'd love to understand the internals.",
    "This is exactly what I was looking for — bookmarked!",
    "I respectfully disagree. In my experience the opposite is true at scale.",
    "Solid advice. We adopted this pattern last quarter and it worked great.",
    "Has anyone benchmarked this? I'm curious about the performance impact.",
    "This thread is gold. More discussions like this please!",
    "We use a similar setup at work. One gotcha to watch out for is memory leaks.",
    "Good write-up! I'd add that error handling is also critical here.",
    "I switched from the old approach to this one and never looked back.",
    "Nice! Would love to see a follow-up thread on advanced use cases.",
    "This reminded me of a talk I saw at PyCon. Very relevant.",
    "Just deployed this in staging and the results are promising.",
    "Would be great to see a benchmark comparing the two approaches.",
    "We ran into the exact same issue last sprint. Here is how we fixed it.",
    "Underrated topic! More people should be talking about this.",
    "Adding to the list: do not forget about edge cases with concurrent requests.",
]

for i, tid in enumerate(thread_ids):
    num_comments = random.randint(4, 7)
    for _ in range(num_comments):
        commenter = random.choice(usernames)
        text = random.choice(comments_pool)
        r = client.post("/comments",
                        json={"thread_id": tid, "content": text},
                        headers=auth(tokens[commenter]))
        if r.status_code == 200:
            cid = r.json()["id"]
            comment_ids.append({"id": cid, "thread_id": tid, "author": commenter})
            print(f"  ✔ {commenter} commented on thread {tid} (comment {cid})")

# ── 7. Reply to comments (10 replies with some @mentions) ───────────────────
print("\n=== Replying to Comments ===")
reply_pool = [
    "Well said! I couldn't agree more.",
    "Thanks for the reply — that clears things up.",
    "Hmm, I see your point but what about edge cases in production?",
    "Exactly! This is the pattern we follow too.",
    "Good catch — I missed that detail. Updated my approach.",
    "Let me test this out and report back.",
]

replies_made = 0
for c in random.sample(comment_ids, k=min(20, len(comment_ids))):
    replier = random.choice([u for u in usernames if u != c["author"]])
    # Add @mention in ~40% of replies
    if random.random() < 0.4:
        text = f"@{c['author']} {random.choice(reply_pool)}"
    else:
        text = random.choice(reply_pool)
    r = client.post("/comments",
                    json={"thread_id": c["thread_id"], "content": text,
                          "parent_comment_id": c["id"]},
                    headers=auth(tokens[replier]))
    if r.status_code == 200:
        replies_made += 1
        print(f"  ✔ {replier} replied to comment {c['id']}")

# ── 8. Like comments (10-15 random likes) ────────────────────────────────────
print("\n=== Liking Comments ===")
for c in random.sample(comment_ids, k=min(25, len(comment_ids))):
    liker = random.choice([u for u in usernames if u != c["author"]])
    r = client.post(f"/comments/{c['id']}/like", headers=auth(tokens[liker]))
    if r.status_code == 200:
        data = r.json()
        if data.get("liked"):
            print(f"  ✔ {liker} liked comment {c['id']}")

# ── 9. Some users leave communities (triggers notifications) ────────────────
print("\n=== Community Leave Events ===")
if len(community_ids) >= 2:
    for name in ["frank", "tina"]:
        if name in tokens:
            r = client.delete(f"/communities/{community_ids[0]}/leave", headers=auth(tokens[name]))
            if r.status_code == 200:
                print(f"  ✔ {name} left community {community_ids[0]}")

# Small delay so Kafka processes all events
time.sleep(2)

# ── Done ─────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("✅ Seed data complete!")
print("=" * 60)
print(f"   Users:        {len(users)}")
print(f"   Communities:  {len(community_ids)}")
print(f"   Threads:      {len(thread_ids)}")
print(f"   Comments:     {len(comment_ids)} + {replies_made} replies")
print(f"\n   All passwords: {PASSWORD}")
print(f"   Admin:  alice")
print(f"   Mod:    bob")
print(f"   Members: charlie, diana, eve, frank, grace, henry, ivy, jack")
print(f"            karen, leo, mia, noah, olivia, peter, quinn, rachel, sam, tina")
print("=" * 60)
