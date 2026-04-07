"""Async tests for community_service endpoints."""
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
    assert data["service"] == "community"
    assert data["db"] == "connected"


# ── Community CRUD ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_community(client: AsyncClient, auth_token: str):
    resp = await client.post(
        "/communities",
        json={"name": "Python Devs", "description": "All things Python"},
        headers=_auth(auth_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Python Devs"
    assert data["slug"] == "python-devs"
    assert data["member_count"] == 1


@pytest.mark.asyncio
async def test_create_community_unauthenticated(client: AsyncClient):
    resp = await client.post(
        "/communities",
        json={"name": "No Auth", "description": "fail"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_duplicate_community(client: AsyncClient, auth_token: str):
    await client.post(
        "/communities",
        json={"name": "Unique Name"},
        headers=_auth(auth_token),
    )
    resp = await client.post(
        "/communities",
        json={"name": "Unique Name"},
        headers=_auth(auth_token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_communities(client: AsyncClient, auth_token: str):
    await client.post(
        "/communities",
        json={"name": "C1", "description": "d1"},
        headers=_auth(auth_token),
    )
    await client.post(
        "/communities",
        json={"name": "C2", "description": "d2"},
        headers=_auth(auth_token),
    )
    resp = await client.get("/communities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_community(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/communities",
        json={"name": "Detail Test", "description": "desc"},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    resp = await client.get(f"/communities/{cid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Detail Test"


@pytest.mark.asyncio
async def test_get_community_by_slug(client: AsyncClient, auth_token: str):
    await client.post(
        "/communities",
        json={"name": "Slug Test"},
        headers=_auth(auth_token),
    )
    resp = await client.get("/communities/slug-test")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Slug Test"


@pytest.mark.asyncio
async def test_get_community_not_found(client: AsyncClient):
    resp = await client.get("/communities/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_community(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/communities",
        json={"name": "Old Name", "description": "old"},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    resp = await client.put(
        f"/communities/{cid}",
        json={"name": "New Name", "description": "new"},
        headers=_auth(auth_token),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["slug"] == "new-name"


@pytest.mark.asyncio
async def test_update_community_forbidden(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post(
        "/communities",
        json={"name": "Owner Only"},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    resp = await client.put(
        f"/communities/{cid}",
        json={"description": "hacked"},
        headers=_auth(second_user_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_community(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/communities",
        json={"name": "ToDelete", "description": "bye"},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    resp = await client.delete(f"/communities/{cid}", headers=_auth(auth_token))
    assert resp.status_code == 200

    resp = await client.get(f"/communities/{cid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_community_forbidden(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post(
        "/communities",
        json={"name": "No Delete"},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    resp = await client.delete(f"/communities/{cid}", headers=_auth(second_user_token))
    assert resp.status_code == 403


# ── Membership ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_join_community(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post(
        "/communities",
        json={"name": "Joinable"},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    resp = await client.post(f"/communities/{cid}/join", headers=_auth(second_user_token))
    assert resp.status_code == 200
    assert "Joined" in resp.json()["message"]


@pytest.mark.asyncio
async def test_join_community_already_member(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post(
        "/communities",
        json={"name": "Double Join"},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    await client.post(f"/communities/{cid}/join", headers=_auth(second_user_token))
    resp = await client.post(f"/communities/{cid}/join", headers=_auth(second_user_token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_leave_community(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post(
        "/communities",
        json={"name": "Leavable"},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    await client.post(f"/communities/{cid}/join", headers=_auth(second_user_token))
    resp = await client.delete(f"/communities/{cid}/leave", headers=_auth(second_user_token))
    assert resp.status_code == 200
    assert "Left" in resp.json()["message"]


@pytest.mark.asyncio
async def test_owner_cannot_leave(client: AsyncClient, auth_token: str):
    create = await client.post(
        "/communities",
        json={"name": "Owned"},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    resp = await client.delete(f"/communities/{cid}/leave", headers=_auth(auth_token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_members(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post(
        "/communities",
        json={"name": "Members Test"},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    await client.post(f"/communities/{cid}/join", headers=_auth(second_user_token))
    resp = await client.get(f"/communities/{cid}/members")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── Role Management ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_change_member_role(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post(
        "/communities",
        json={"name": "Role Test"},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    await client.post(f"/communities/{cid}/join", headers=_auth(second_user_token))

    # Get second user's ID from the members list
    members = (await client.get(f"/communities/{cid}/members")).json()
    second_uid = [m for m in members if m["username"] == "seconduser"][0]["user_id"]

    resp = await client.put(
        f"/communities/{cid}/members/{second_uid}/role?role=moderator",
        headers=_auth(auth_token),
    )
    assert resp.status_code == 200
    assert "moderator" in resp.json()["message"]


@pytest.mark.asyncio
async def test_change_owner_role_forbidden(client: AsyncClient, auth_token: str, admin_token: str):
    create = await client.post(
        "/communities",
        json={"name": "Owner Protected"},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]

    # Get owner user ID from members list
    members = (await client.get(f"/communities/{cid}/members")).json()
    owner_uid = members[0]["user_id"]

    resp = await client.put(
        f"/communities/{cid}/members/{owner_uid}/role?role=member",
        headers=_auth(admin_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_change_role_not_authorized(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post(
        "/communities",
        json={"name": "Role Auth Test"},
        headers=_auth(auth_token),
    )
    cid = create.json()["id"]
    await client.post(f"/communities/{cid}/join", headers=_auth(second_user_token))

    members = (await client.get(f"/communities/{cid}/members")).json()
    second_uid = [m for m in members if m["username"] == "seconduser"][0]["user_id"]

    resp = await client.put(
        f"/communities/{cid}/members/{second_uid}/role?role=moderator",
        headers=_auth(second_user_token),
    )
    assert resp.status_code == 403


# ── My Communities ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_my_communities(client: AsyncClient, auth_token: str, second_user_token: str):
    # Create a community as testuser
    await client.post(
        "/communities",
        json={"name": "My Owned"},
        headers=_auth(auth_token),
    )
    # Create one as second user and join with testuser
    create2 = await client.post(
        "/communities",
        json={"name": "Joined One"},
        headers=_auth(second_user_token),
    )
    cid2 = create2.json()["id"]
    await client.post(f"/communities/{cid2}/join", headers=_auth(auth_token))

    resp = await client.get("/communities/my", headers=_auth(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["owned"]) == 1
    assert len(data["member_of"]) == 1


@pytest.mark.asyncio
async def test_search_communities(client: AsyncClient, auth_token: str):
    await client.post(
        "/communities",
        json={"name": "Python Club"},
        headers=_auth(auth_token),
    )
    await client.post(
        "/communities",
        json={"name": "Java Club"},
        headers=_auth(auth_token),
    )
    resp = await client.get("/communities?search=Python")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["name"] == "Python Club"


# ── Pagination ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_communities_pagination(client: AsyncClient, auth_token: str):
    for i in range(5):
        await client.post("/communities", json={"name": f"Page {i}"}, headers=_auth(auth_token))
    resp = await client.get("/communities?skip=0&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2
    assert resp.json()["total"] == 5


# ── Leave non-member ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_leave_not_a_member(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post("/communities", json={"name": "Not Joined"}, headers=_auth(auth_token))
    cid = create.json()["id"]
    resp = await client.delete(f"/communities/{cid}/leave", headers=_auth(second_user_token))
    assert resp.status_code == 400


# ── Change role invalid value ─────────────────────────────────────

@pytest.mark.asyncio
async def test_change_role_invalid(client: AsyncClient, auth_token: str, second_user_token: str):
    create = await client.post("/communities", json={"name": "Invalid Role"}, headers=_auth(auth_token))
    cid = create.json()["id"]
    await client.post(f"/communities/{cid}/join", headers=_auth(second_user_token))
    members = (await client.get(f"/communities/{cid}/members")).json()
    second_uid = [m for m in members if m["username"] == "seconduser"][0]["user_id"]
    resp = await client.put(
        f"/communities/{cid}/members/{second_uid}/role?role=superadmin",
        headers=_auth(auth_token),
    )
    assert resp.status_code == 400


# ── Admin can delete any community ────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_delete_community(client: AsyncClient, auth_token: str, admin_token: str):
    create = await client.post("/communities", json={"name": "Admin Del"}, headers=_auth(auth_token))
    cid = create.json()["id"]
    resp = await client.delete(f"/communities/{cid}", headers=_auth(admin_token))
    assert resp.status_code == 200


# ── Update duplicate name ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_community_duplicate_name(client: AsyncClient, auth_token: str):
    await client.post("/communities", json={"name": "Name A"}, headers=_auth(auth_token))
    create2 = await client.post("/communities", json={"name": "Name B"}, headers=_auth(auth_token))
    cid2 = create2.json()["id"]
    resp = await client.put(
        f"/communities/{cid2}",
        json={"name": "Name A"},
        headers=_auth(auth_token),
    )
    assert resp.status_code == 409
