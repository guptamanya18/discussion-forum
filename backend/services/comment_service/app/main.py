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
_file = RotatingFileHandler(os.path.join(LOG_DIR, "comment_service.log"), maxBytes=5_000_000, backupCount=3)
_file.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_console, _file])
logger = logging.getLogger("comment_service")

from app.database import engine, Base
from app.models import user, comment, like  # noqa: F401
from app.routes import comment_routes
from app.kafka_producer import kafka_producer
from app.kafka_consumer import start_kafka_consumer
from app.core.exceptions import AppException, app_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    for _ in range(5):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.execute(
                    sqlalchemy.text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar VARCHAR DEFAULT NULL"
                    )
                )
            break
        except Exception:
            await asyncio.sleep(1)
    await kafka_producer.start()
    consumer_task = asyncio.create_task(start_kafka_consumer())
    logger.info("Comment service started successfully")
    yield
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await kafka_producer.stop()


app = FastAPI(title="Comment Service", lifespan=lifespan)
app.add_exception_handler(AppException, app_exception_handler)
app.include_router(comment_routes.router)


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
    return {"service": "comment", "status": "ok" if db_status == "connected" else "degraded", "db": db_status, "kafka": kafka_status}