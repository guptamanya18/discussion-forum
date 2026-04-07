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
async def test_create_thread_unauthenticated(client: AsyncClient):
    resp = await client.post(
        "/threads",
        json={"title": "Fail", "description": "no auth"},
    )
    assert resp.status_code in (401, 403)


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
async def test_list_threads_search(client: AsyncClient, auth_token: str):
    await client.post("/threads", json={"title": "Python Tips", "description": "d"}, headers=_auth(auth_token))
    await client.post("/threads", json={"title": "Java Tips", "description": "d"}, headers=_auth(auth_token))
    resp = await client.get("/threads?search=Python")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["title"] == "Python Tips"


@pytest.mark.asyncio
async def test_list_threads_sort_oldest(client: AsyncClient, auth_token: str):
    await client.post("/threads", json={"title": "First", "description": "d"}, headers=_auth(auth_token))
    await client.post("/threads", json={"title": "Second", "description": "d"}, headers=_auth(auth_token))
    resp = await client.get("/threads?sort_by=oldest")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items[0]["title"] == "First"


@pytest.mark.asyncio
async def test_list_threads_filter_tag(client: AsyncClient, auth_token: str):
    await client.post("/threads", json={"title": "T1", "description": "d", "tags": ["python"]}, headers=_auth(auth_token))
    await client.post("/threads", json={"title": "T2", "description": "d", "tags": ["java"]}, headers=_auth(auth_token))
    resp = await client.get("/threads?tag=python")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


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
async def test_update_thread_forbidden(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post(
        "/threads",
        json={"title": "Owner Only", "description": "d"},
        headers=_auth(auth_token),
    )
    tid = create.json()["id"]
    resp = await client.put(
        f"/threads/{tid}",
        json={"title": "Hacked"},
        headers=_auth(second_user_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_thread_not_found(client: AsyncClient, auth_token: str):
    resp = await client.put("/threads/999", json={"title": "X"}, headers=_auth(auth_token))
    assert resp.status_code == 404


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
async def test_delete_thread_by_admin(client: AsyncClient, auth_token: str, admin_token: str):
    create = await client.post(
        "/threads",
        json={"title": "AdminDelete", "description": "d"},
        headers=_auth(auth_token),
    )
    tid = create.json()["id"]
    resp = await client.delete(f"/threads/{tid}", headers=_auth(admin_token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_thread_forbidden(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post(
        "/threads",
        json={"title": "NoDelete", "description": "d"},
        headers=_auth(auth_token),
    )
    tid = create.json()["id"]
    resp = await client.delete(f"/threads/{tid}", headers=_auth(second_user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_thread_not_found(client: AsyncClient, auth_token: str):
    resp = await client.delete("/threads/999", headers=_auth(auth_token))
    assert resp.status_code == 404


# ── Like ──────────────────────────────────────────────────────────

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


@pytest.mark.asyncio
async def test_get_thread_likes_list(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/threads",
        json={"title": "Likes List", "description": "d"},
        headers=_auth(auth_token),
    )
    tid = create.json()["id"]
    await client.post(f"/threads/{tid}/like", headers=_auth(auth_token))
    resp = await client.get(f"/threads/{tid}/likes")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_get_thread_likes_not_found(client: AsyncClient):
    resp = await client.get("/threads/999/likes")
    assert resp.status_code == 404


# ── Reports ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_thread(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post(
        "/threads",
        json={"title": "Reportable", "description": "bad content"},
        headers=_auth(auth_token),
    )
    tid = create.json()["id"]
    resp = await client.post(
        f"/threads/{tid}/report",
        json={"reason": "spam", "details": "This is spam"},
        headers=_auth(second_user_token),
    )
    assert resp.status_code == 200
    assert resp.json()["reason"] == "spam"
    assert resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_report_own_thread(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/threads",
        json={"title": "SelfReport", "description": "d"},
        headers=_auth(auth_token),
    )
    tid = create.json()["id"]
    resp = await client.post(
        f"/threads/{tid}/report",
        json={"reason": "spam"},
        headers=_auth(auth_token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_report_duplicate(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post(
        "/threads",
        json={"title": "DupReport", "description": "d"},
        headers=_auth(auth_token),
    )
    tid = create.json()["id"]
    await client.post(f"/threads/{tid}/report", json={"reason": "spam"}, headers=_auth(second_user_token))
    resp = await client.post(f"/threads/{tid}/report", json={"reason": "spam"}, headers=_auth(second_user_token))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_report_nonexistent_thread(client: AsyncClient, auth_token: str):
    resp = await client.post("/threads/999/report", json={"reason": "spam"}, headers=_auth(auth_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_reports_admin(client: AsyncClient, auth_token: str, second_user_token: str, admin_token: str):
    create = await client.post(
        "/threads",
        json={"title": "Reported", "description": "d"},
        headers=_auth(auth_token),
    )
    tid = create.json()["id"]
    await client.post(f"/threads/{tid}/report", json={"reason": "spam"}, headers=_auth(second_user_token))

    resp = await client.get("/reports", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_list_reports_forbidden(client: AsyncClient, auth_token: str):
    resp = await client.get("/reports", headers=_auth(auth_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_report_status(client: AsyncClient, auth_token: str, second_user_token: str, admin_token: str):
    create = await client.post(
        "/threads",
        json={"title": "StatusReport", "description": "d"},
        headers=_auth(auth_token),
    )
    tid = create.json()["id"]
    report = await client.post(f"/threads/{tid}/report", json={"reason": "spam"}, headers=_auth(second_user_token))
    rid = report.json()["id"]

    resp = await client.put(f"/reports/{rid}/status?status=reviewed", headers=_auth(admin_token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_report_status_invalid(client: AsyncClient, admin_token: str):
    resp = await client.put("/reports/999/status?status=invalid", headers=_auth(admin_token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_report_status_forbidden(client: AsyncClient, auth_token: str):
    resp = await client.put("/reports/1/status?status=reviewed", headers=_auth(auth_token))
    assert resp.status_code == 403
