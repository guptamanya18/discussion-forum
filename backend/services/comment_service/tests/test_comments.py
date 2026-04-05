"""Async tests for comment_service endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Health ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "comment"
    assert data["db"] == "connected"


# ── Comment CRUD ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_comment(client: AsyncClient, auth_token: str):
    resp = await client.post(
        "/comments",
        json={"content": "First comment", "thread_id": 1},
        headers=_auth(auth_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "First comment"
    assert data["thread_id"] == 1


@pytest.mark.asyncio
async def test_create_comment_unauthenticated(client: AsyncClient):
    resp = await client.post(
        "/comments",
        json={"content": "No auth", "thread_id": 1},
    )
    assert resp.status_code == 401  # no bearer token


@pytest.mark.asyncio
async def test_get_comment(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/comments",
        json={"content": "Get me", "thread_id": 1},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    resp = await client.get(f"/comments/{cid}")
    assert resp.status_code == 200
    assert resp.json()["content"] == "Get me"


@pytest.mark.asyncio
async def test_get_comment_not_found(client: AsyncClient):
    resp = await client.get("/comments/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_comment(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/comments",
        json={"content": "Old", "thread_id": 1},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    resp = await client.put(
        f"/comments/{cid}",
        json={"content": "Updated"},
        headers=_auth(auth_token),
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "Updated"


@pytest.mark.asyncio
async def test_delete_comment(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/comments",
        json={"content": "Bye", "thread_id": 1},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    resp = await client.delete(f"/comments/{cid}", headers=_auth(auth_token))
    assert resp.status_code == 200


# ── Reply to comment ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reply_to_comment(client: AsyncClient, auth_token: str, second_user_token: str):
    parent = await client.post(
        "/comments",
        json={"content": "Parent", "thread_id": 1},
        headers=_auth(auth_token),
    )
    pid = parent.json()["id"]
    reply = await client.post(
        "/comments",
        json={"content": "Reply", "thread_id": 1, "parent_comment_id": pid},
        headers=_auth(second_user_token),
    )
    assert reply.status_code == 200
    assert reply.json()["parent_comment_id"] == pid


@pytest.mark.asyncio
async def test_reply_to_nonexistent_parent(client: AsyncClient, auth_token: str):
    resp = await client.post(
        "/comments",
        json={"content": "Orphan", "thread_id": 1, "parent_comment_id": 999},
        headers=_auth(auth_token),
    )
    assert resp.status_code == 404


# ── Like toggle ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_like_toggle(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/comments",
        json={"content": "Like me", "thread_id": 1},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]

    # First like → liked=True
    resp1 = await client.post(f"/comments/{cid}/like", headers=_auth(auth_token))
    assert resp1.status_code == 200
    assert resp1.json()["liked"] is True
    assert resp1.json()["like_count"] == 1

    # Second like → unliked
    resp2 = await client.post(f"/comments/{cid}/like", headers=_auth(auth_token))
    assert resp2.status_code == 200
    assert resp2.json()["liked"] is False
    assert resp2.json()["like_count"] == 0


# ── Thread comment counts ────────────────────────────────────────

@pytest.mark.asyncio
async def test_thread_comment_counts(client: AsyncClient, auth_token: str):
    await client.post("/comments", json={"content": "c1", "thread_id": 1}, headers=_auth(auth_token))
    await client.post("/comments", json={"content": "c2", "thread_id": 1}, headers=_auth(auth_token))
    await client.post("/comments", json={"content": "c3", "thread_id": 2}, headers=_auth(auth_token))

    resp = await client.get("/comments/thread-counts?thread_ids=1,2,3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["1"] == 2
    assert data["2"] == 1
    assert "3" not in data  # no comments on thread 3
