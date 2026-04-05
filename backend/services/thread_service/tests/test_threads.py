"""Async tests for thread_service endpoints."""
import pytest
from httpx import AsyncClient


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Health ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "thread"
    assert data["db"] == "connected"


# ── Thread CRUD ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_thread(client: AsyncClient, auth_token: str):
    resp = await client.post(
        "/threads",
        json={"title": "First thread", "description": "Hello", "tags": ["python"]},
        headers=_auth(auth_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "First thread"
    assert data["tags"] == ["python"]
    assert data["status"] == "open"


@pytest.mark.asyncio
async def test_list_threads(client: AsyncClient, auth_token: str):
    await client.post(
        "/threads",
        json={"title": "T1", "description": "d1"},
        headers=_auth(auth_token),
    )
    await client.post(
        "/threads",
        json={"title": "T2", "description": "d2"},
        headers=_auth(auth_token),
    )
    resp = await client.get("/threads")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2
    assert resp.json()["total"] == 2


@pytest.mark.asyncio
async def test_get_thread(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/threads",
        json={"title": "Detail", "description": "desc"},
        headers=_auth(auth_token),
    )
    tid = create.json()["id"]
    resp = await client.get(f"/threads/{tid}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Detail"


@pytest.mark.asyncio
async def test_get_thread_not_found(client: AsyncClient):
    resp = await client.get("/threads/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_thread(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/threads",
        json={"title": "Old", "description": "old"},
        headers=_auth(auth_token),
    )
    tid = create.json()["id"]
    resp = await client.put(
        f"/threads/{tid}",
        json={"title": "New"},
        headers=_auth(auth_token),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"


@pytest.mark.asyncio
async def test_delete_thread(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/threads",
        json={"title": "ToDelete", "description": "bye"},
        headers=_auth(auth_token),
    )
    tid = create.json()["id"]
    resp = await client.delete(f"/threads/{tid}", headers=_auth(auth_token))
    assert resp.status_code == 200

    # Verify it's gone (soft-delete)
    resp = await client.get(f"/threads/{tid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_like_thread(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/threads",
        json={"title": "Likeable", "description": "like me"},
        headers=_auth(auth_token),
    )
    tid = create.json()["id"]

    # Like
    resp = await client.post(f"/threads/{tid}/like", headers=_auth(auth_token))
    assert resp.status_code == 200
    assert resp.json()["liked"] is True
    assert resp.json()["like_count"] == 1

    # Unlike (toggle)
    resp = await client.post(f"/threads/{tid}/like", headers=_auth(auth_token))
    assert resp.status_code == 200
    assert resp.json()["liked"] is False
    assert resp.json()["like_count"] == 0
