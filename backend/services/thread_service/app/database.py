from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

DATABASE_URL = settings.database_url


# connects to db asynchronously (non-blocking)
engine = create_async_engine(DATABASE_URL)

AsyncSessionLocal = sessionmaker(  # factory to create db sessions
    engine,
    class_=AsyncSession,  # tells sqlalchemy to use async session
    expire_on_commit=False,
    autoflush=False,  # prevents automatic db writes before queries
)

# base class for all models
Base = declarative_base()


# dependency function  --  async generator, yields session, ensures close in finally
async def get_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()
