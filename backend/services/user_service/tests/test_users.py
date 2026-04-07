"""Async tests for user_service endpoints."""
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
    assert data["service"] == "user"
    assert data["db"] == "connected"


# ── Registration ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    resp = await client.post("/users/register", json={
        "username": "newuser",
        "email": "new@example.com",
        "password": "pass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert data["role"] == "member"


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    payload = {"username": "dup", "email": "dup@example.com", "password": "pass123"}
    await client.post("/users/register", json=payload)
    resp = await client.post("/users/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/users/register", json={
        "username": "shortpw",
        "email": "sp@example.com",
        "password": "ab1",
    })
    assert resp.status_code == 422  # pydantic validation


# ── Login ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/users/register", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "pass123",
    })
    resp = await client.post("/auth/login", data={
        "username": "loginuser",
        "password": "pass123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/users/register", json={
        "username": "wrongpw",
        "email": "wrong@example.com",
        "password": "pass123",
    })
    resp = await client.post("/auth/login", data={
        "username": "wrongpw",
        "password": "wrongpass1",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/auth/login", data={
        "username": "ghost",
        "password": "pass123",
    })
    assert resp.status_code == 401


# ── Authenticated endpoints ───────────────────────────────────────

@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_token: str):
    resp = await client.get("/auth/me", headers=_auth(auth_token))
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient, auth_token: str):
    resp = await client.put(
        "/users/profile",
        json={"bio": "Hello world"},
        headers=_auth(auth_token),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_unauthorized_without_token(client: AsyncClient):
    resp = await client.get("/auth/me")
    assert resp.status_code in (401, 403)


# ── Get user profile ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_profile(client: AsyncClient, auth_token: str):
    me = await client.get("/auth/me", headers=_auth(auth_token))
    uid = me.json()["id"]
    resp = await client.get(f"/users/{uid}")
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_get_user_profile_not_found(client: AsyncClient):
    resp = await client.get("/users/999")
    assert resp.status_code == 404


# ── Member dashboard ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_member_dashboard(client: AsyncClient, auth_token: str):
    resp = await client.get("/users/me/dashboard", headers=_auth(auth_token))
    assert resp.status_code == 200
    assert resp.json()["user"]["username"] == "testuser"


# ── Admin endpoints ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_stats(client: AsyncClient, admin_token: str):
    resp = await client.get("/users/admin/stats", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert "total_users" in resp.json()
    assert "roles" in resp.json()


@pytest.mark.asyncio
async def test_admin_stats_forbidden(client: AsyncClient, auth_token: str):
    resp = await client.get("/users/admin/stats", headers=_auth(auth_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_users(client: AsyncClient, admin_token: str):
    resp = await client.get("/users/admin/users", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_admin_list_users_search(client: AsyncClient, admin_token: str):
    resp = await client.get("/users/admin/users?search=admin", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert all("admin" in u["username"] for u in resp.json())


@pytest.mark.asyncio
async def test_admin_set_user_status(client: AsyncClient, admin_token: str, auth_token: str):
    me = await client.get("/auth/me", headers=_auth(auth_token))
    uid = me.json()["id"]
    resp = await client.post(
        f"/users/admin/users/{uid}/status?is_active=false",
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert "deactivated" in resp.json()["message"]


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_self(client: AsyncClient, admin_token: str):
    me = await client.get("/auth/me", headers=_auth(admin_token))
    uid = me.json()["id"]
    resp = await client.post(
        f"/users/admin/users/{uid}/status?is_active=false",
        headers=_auth(admin_token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_admin_delete_user(client: AsyncClient, admin_token: str):
    # Register a user to delete
    await client.post("/users/register", json={
        "username": "deleteme",
        "email": "del@example.com",
        "password": "pass123",
    })
    from app.models.user import User
    from sqlalchemy import select
    from tests.conftest import TestSession
    async with TestSession() as session:
        result = await session.execute(select(User).where(User.username == "deleteme"))
        user = result.scalars().first()
        uid = user.id

    resp = await client.delete(f"/users/admin/users/{uid}", headers=_auth(admin_token))
    assert resp.status_code == 200

    # Verify deleted
    resp = await client.get(f"/users/{uid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_cannot_delete_self(client: AsyncClient, admin_token: str):
    me = await client.get("/auth/me", headers=_auth(admin_token))
    uid = me.json()["id"]
    resp = await client.delete(f"/users/admin/users/{uid}", headers=_auth(admin_token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_admin_change_role(client: AsyncClient, admin_token: str, auth_token: str):
    me = await client.get("/auth/me", headers=_auth(auth_token))
    uid = me.json()["id"]
    resp = await client.put(
        f"/users/{uid}",
        json={"role": "moderator"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "moderator"


@pytest.mark.asyncio
async def test_change_role_forbidden(client: AsyncClient, auth_token: str):
    resp = await client.put("/users/1", json={"role": "admin"}, headers=_auth(auth_token))
    assert resp.status_code == 403


# ── Moderator endpoints ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_mod_stats(client: AsyncClient, admin_token: str):
    resp = await client.get("/users/mod/stats", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert "total_users" in resp.json()
    assert "recent_users" in resp.json()


@pytest.mark.asyncio
async def test_mod_list_users(client: AsyncClient, admin_token: str):
    resp = await client.get("/users/mod/users", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert "users" in resp.json()


@pytest.mark.asyncio
async def test_mod_endpoints_forbidden_for_member(client: AsyncClient, auth_token: str):
    resp = await client.get("/users/mod/stats", headers=_auth(auth_token))
    assert resp.status_code == 403
    resp = await client.get("/users/mod/users", headers=_auth(auth_token))
    assert resp.status_code == 403


# ── Forgot / Reset password ──────────────────────────────────────

@pytest.mark.asyncio
async def test_forgot_password(client: AsyncClient):
    await client.post("/users/register", json={
        "username": "forgotuser",
        "email": "forgot@example.com",
        "password": "pass123",
    })
    resp = await client.post("/auth/forgot-password", json={"email": "forgot@example.com"})
    assert resp.status_code == 200
    assert "reset link" in resp.json()["message"].lower() or "sent" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_forgot_password_nonexistent(client: AsyncClient):
    resp = await client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 200  # Always returns same message (no email enumeration)


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient):
    resp = await client.post("/auth/reset-password", json={
        "token": "invalid-token",
        "new_password": "newpass123",
    })
    assert resp.status_code == 400
