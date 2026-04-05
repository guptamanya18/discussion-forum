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
