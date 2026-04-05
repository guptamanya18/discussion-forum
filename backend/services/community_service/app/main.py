import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler
import sqlalchemy
from contextlib import asynccontextmanager
from fastapi import FastAPI

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
_fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
_console = logging.StreamHandler()
_console.setFormatter(_fmt)
_file = RotatingFileHandler(os.path.join(LOG_DIR, "community_service.log"), maxBytes=5_000_000, backupCount=3)
_file.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_console, _file])
logger = logging.getLogger("community_service")

from app.database import engine, Base
from app.models import user, community, community_member
from app.models.community import generate_slug
from app.routes import community_routes
from app.kafka_producer import kafka_producer
from app.kafka_consumer import start_kafka_consumer
from app.core.exceptions import AppException, app_exception_handler

@asynccontextmanager
async def lifespan(app:FastAPI):
    for _ in range(5):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.execute(
                    sqlalchemy.text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar VARCHAR DEFAULT NULL"
                    )
                )
                # Add slug column if not exists
                await conn.execute(
                    sqlalchemy.text(
                        "ALTER TABLE communities ADD COLUMN IF NOT EXISTS slug VARCHAR UNIQUE"
                    )
                )
            # Backfill slugs for communities that don't have one
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                from app.models.community import Community
                result = await db.execute(
                    sqlalchemy.text("SELECT id, name FROM communities WHERE slug IS NULL")
                )
                rows = result.fetchall()
                for row in rows:
                    slug = generate_slug(row[1])
                    # Ensure uniqueness
                    existing = await db.execute(
                        sqlalchemy.text("SELECT id FROM communities WHERE slug = :slug"),
                        {"slug": slug},
                    )
                    if existing.fetchone():
                        slug = f"{slug}-{row[0]}"
                    await db.execute(
                        sqlalchemy.text("UPDATE communities SET slug = :slug WHERE id = :id"),
                        {"slug": slug, "id": row[0]},
                    )
                await db.commit()
            break
        except Exception:
            await asyncio.sleep(1)
    await kafka_producer.start()
    consumer_task = asyncio.create_task(start_kafka_consumer())
    logger.info("Community service started successfully")
    yield
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await kafka_producer.stop()

app=FastAPI(title="Community Service", lifespan=lifespan)
app.add_exception_handler(AppException, app_exception_handler)
app.include_router(community_routes.router)

@app.get("/health")
async def health():
    try:
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error("Health check DB failure: %s", e)
        db_status = "disconnected"
    kafka_status = "connected" if kafka_producer._producer else "disconnected"
    return {"service": "community", "status": "ok" if db_status == "connected" else "degraded", "db": db_status, "kafka": kafka_status}