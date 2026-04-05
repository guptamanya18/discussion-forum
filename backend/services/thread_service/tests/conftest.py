"""
Shared fixtures for thread_service async tests.
Uses SQLite in-memory DB, mocks Kafka producer.
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-12345")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
import app.database as db_module
from app.main import app
from app.models.user import User

# ── Test engine ───────────────────────────────────────────────────
test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
TestSession = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
db_module.engine = test_engine

# ── Mock Kafka producer ──────────────────────────────────────────
_mock_kafka = MagicMock()
_mock_kafka.send = AsyncMock(return_value=None)
_mock_kafka._producer = True

import app.routes.thread_routes as routes_mod
import app.main as main_mod

routes_mod.kafka_producer = _mock_kafka
main_mod.kafka_producer = _mock_kafka


async def _override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


# ── Fixtures ──────────────────────────────────────────────────────
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
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
async def auth_token():
    """Create a user directly in DB and return a JWT token."""
    async with TestSession() as session:
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="unused",
            role="member",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = jwt.encode(
            {"sub": str(user.id)},
            os.environ["SECRET_KEY"],
            algorithm=os.environ["ALGORITHM"],
        )
        return token
