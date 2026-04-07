"""
Shared fixtures for user_service async tests.
Uses SQLite (aiosqlite) in-memory DB + httpx AsyncClient.
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-12345")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
import app.database as db_module
from app.main import app

# ── Test engine (SQLite in-memory) ────────────────────────────────
test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
TestSession = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

# Override the real Postgres engine so health-check uses SQLite too
db_module.engine = test_engine

# ── Mock Kafka producer ──────────────────────────────────────────
_mock_kafka = MagicMock()
_mock_kafka.send = AsyncMock(return_value=None)
_mock_kafka._producer = True

import app.routes.user_routes as user_routes_mod
import app.main as main_mod

user_routes_mod.kafka_producer = _mock_kafka
main_mod.kafka_producer = _mock_kafka

# Mock external service URL
user_routes_mod.NOTIFICATION_SERVICE_URL = "http://127.0.0.1:1"


async def _override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


# ── Fixtures ──────────────────────────────────────────────────────
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient) -> str:
    """Register a test user and return their JWT token."""
    await client.post("/users/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "pass123",
    })
    resp = await client.post("/auth/login", data={
        "username": "testuser",
        "password": "pass123",
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    """Register, login, then promote to admin via direct DB update."""
    await client.post("/users/register", json={
        "username": "adminuser",
        "email": "admin@example.com",
        "password": "admin123",
    })
    # Promote to admin directly in DB
    from app.models.user import User
    from sqlalchemy import select, update
    async with TestSession() as session:
        await session.execute(
            update(User).where(User.username == "adminuser").values(role="admin")
        )
        await session.commit()
    resp = await client.post("/auth/login", data={
        "username": "adminuser",
        "password": "admin123",
    })
    return resp.json()["access_token"]
