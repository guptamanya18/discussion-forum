"""Async tests for notification_service endpoints."""
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
    assert data["service"] == "notification"
    assert data["db"] == "connected"


# ── Emit (internal endpoint) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_emit_notification(client: AsyncClient, auth_token):
    token, user_id = auth_token
    resp = await client.post(
        "/notifications/emit",
        json={
            "user_id": user_id,
            "type": "thread_reply",
            "message": "Someone replied to your thread",
            "reference_id": 42,
        },
    )
    assert resp.status_code == 200
    assert "id" in resp.json()


# ── List Notifications ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_notifications(client: AsyncClient, auth_token):
    token, user_id = auth_token
    # Create two notifications
    await client.post(
        "/notifications/emit",
        json={"user_id": user_id, "type": "reply", "message": "Notif 1"},
    )
    await client.post(
        "/notifications/emit",
        json={"user_id": user_id, "type": "like", "message": "Notif 2"},
    )

    resp = await client.get("/notifications", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_notifications_only_own(client: AsyncClient, auth_token, second_user_token):
    token1, uid1 = auth_token
    token2, uid2 = second_user_token

    # Create notification for user 1
    await client.post(
        "/notifications/emit",
        json={"user_id": uid1, "type": "reply", "message": "For user1"},
    )
    # Create notification for user 2
    await client.post(
        "/notifications/emit",
        json={"user_id": uid2, "type": "reply", "message": "For user2"},
    )

    # User 1 should only see their own
    resp = await client.get("/notifications", headers=_auth(token1))
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["message"] == "For user1"


# ── Unread Count ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unread_count(client: AsyncClient, auth_token):
    token, user_id = auth_token
    await client.post(
        "/notifications/emit",
        json={"user_id": user_id, "type": "reply", "message": "Unread 1"},
    )
    await client.post(
        "/notifications/emit",
        json={"user_id": user_id, "type": "like", "message": "Unread 2"},
    )

    resp = await client.get("/notifications/unread-count", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


# ── Mark Read ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_read(client: AsyncClient, auth_token):
    token, user_id = auth_token
    create = await client.post(
        "/notifications/emit",
        json={"user_id": user_id, "type": "reply", "message": "Read me"},
    )
    nid = create.json()["id"]

    resp = await client.put(f"/notifications/{nid}/read", headers=_auth(token))
    assert resp.status_code == 200

    # Verify unread count dropped
    count_resp = await client.get("/notifications/unread-count", headers=_auth(token))
    assert count_resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_mark_read_not_found(client: AsyncClient, auth_token):
    token, _ = auth_token
    resp = await client.put("/notifications/999/read", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mark_read_other_user(client: AsyncClient, auth_token, second_user_token):
    """User cannot mark another user's notification as read."""
    _, uid1 = auth_token
    token2, _ = second_user_token

    create = await client.post(
        "/notifications/emit",
        json={"user_id": uid1, "type": "reply", "message": "Private"},
    )
    nid = create.json()["id"]

    # Second user tries to mark it — should get 404 (not their notification)
    resp = await client.put(f"/notifications/{nid}/read", headers=_auth(token2))
    assert resp.status_code == 404


# ── Mark All Read ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_all_read(client: AsyncClient, auth_token):
    token, user_id = auth_token
    await client.post(
        "/notifications/emit",
        json={"user_id": user_id, "type": "reply", "message": "A"},
    )
    await client.post(
        "/notifications/emit",
        json={"user_id": user_id, "type": "like", "message": "B"},
    )

    resp = await client.put("/notifications/read-all", headers=_auth(token))
    assert resp.status_code == 200

    count_resp = await client.get("/notifications/unread-count", headers=_auth(token))
    assert count_resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_list_notifications_unauthenticated(client: AsyncClient):
    resp = await client.get("/notifications")
    assert resp.status_code in (401, 403)


# ── Pagination ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_notifications_pagination(client: AsyncClient, auth_token):
    token, user_id = auth_token
    for i in range(5):
        await client.post(
            "/notifications/emit",
            json={"user_id": user_id, "type": "reply", "message": f"N{i}"},
        )
    resp = await client.get("/notifications?skip=0&limit=2", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2
    assert resp.json()["total"] == 5


# ── Unread count after mark read ──────────────────────────────────

@pytest.mark.asyncio
async def test_unread_count_after_partial_read(client: AsyncClient, auth_token):
    token, user_id = auth_token
    n1 = await client.post("/notifications/emit", json={"user_id": user_id, "type": "a", "message": "m1"})
    await client.post("/notifications/emit", json={"user_id": user_id, "type": "b", "message": "m2"})
    nid = n1.json()["id"]

    await client.put(f"/notifications/{nid}/read", headers=_auth(token))
    resp = await client.get("/notifications/unread-count", headers=_auth(token))
    assert resp.json()["count"] == 1


# ── Emit with reference_id ────────────────────────────────────────

@pytest.mark.asyncio
async def test_emit_with_reference_id(client: AsyncClient, auth_token):
    token, user_id = auth_token
    resp = await client.post(
        "/notifications/emit",
        json={"user_id": user_id, "type": "like", "message": "liked", "reference_id": 42},
    )
    assert resp.status_code == 200

    # Verify reference_id is in the notification
    notifs = await client.get("/notifications", headers=_auth(token))
    assert notifs.json()["items"][0]["reference_id"] == 42
