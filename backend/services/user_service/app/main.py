import asyncio
import logging
import sqlalchemy
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.database import engine, Base, AsyncSessionLocal
from app.models import user  # noqa: F401 – registers table with Base
from app.models.user import User
from app.core.security import hash_password
from app.core.exceptions import AppException, app_exception_handler
from app.routes import auth_routes, user_routes
from app.kafka_producer import kafka_producer

import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
_fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
_console = logging.StreamHandler()
_console.setFormatter(_fmt)
_file = RotatingFileHandler(os.path.join(LOG_DIR, "user_service.log"), maxBytes=5_000_000, backupCount=3)
_file.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_console, _file])
logger = logging.getLogger("user_service")

BOOTSTRAP_ADMIN_USERNAME = "alice"
BOOTSTRAP_ADMIN_EMAIL = "alice@example.com"
BOOTSTRAP_ADMIN_PASSWORD = "pass123"


async def create_bootstrap_admin():
    for attempt in range(5):
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.username == BOOTSTRAP_ADMIN_USERNAME)
                )
                if result.scalars().first() is None:
                    admin = User(
                        username=BOOTSTRAP_ADMIN_USERNAME,
                        email=BOOTSTRAP_ADMIN_EMAIL,
                        hashed_password=hash_password(BOOTSTRAP_ADMIN_PASSWORD),
                        role="admin",
                    )
                    db.add(admin)
                    await db.commit()
                    logger.info("Bootstrap admin '%s' created.", BOOTSTRAP_ADMIN_USERNAME)
                else:
                    logger.info("Bootstrap admin '%s' already exists, skipping.", BOOTSTRAP_ADMIN_USERNAME)
                return
        except Exception as e:
            logger.warning("Bootstrap admin attempt %d failed: %s", attempt+1, e)
            await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    for _ in range(5):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.execute(
                    sqlalchemy.text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR DEFAULT NULL"
                    )
                )
            break
        except Exception:
            await asyncio.sleep(1)
    await kafka_producer.start()
    await create_bootstrap_admin()
    logger.info("User service started successfully")
    yield
    await kafka_producer.stop()


app = FastAPI(title="User & Auth Service", lifespan=lifespan)

# Register custom exception handler (catches all AppException subclasses)
app.add_exception_handler(AppException, app_exception_handler)

app.include_router(auth_routes.router, prefix="/auth")
app.include_router(user_routes.router)

import os
os.makedirs("/app/uploads/avatars", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="/app/uploads"), name="uploads")


@app.get("/health")
async def health():
    """Real connection check — verifies DB is reachable."""
    try:
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error("Health check DB failure: %s", e)
        db_status = "disconnected"
    return {"service": "user", "status": "ok" if db_status == "connected" else "degraded", "db": db_status}
