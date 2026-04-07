"""This file handles the connection to our database for comments."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

DATABASE_URL = settings.database_url

engine = create_async_engine(DATABASE_URL)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()
