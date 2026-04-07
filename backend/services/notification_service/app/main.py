"""This is the main entry point for the notification service."""
import asyncio
import logging
import sqlalchemy
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.models import user, notification
from app.routes import notification_routes, ws_routes
from app.kafka_consumer import start_kafka_consumer
from app.core.exceptions import AppException, app_exception_handler

import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
_fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
_console = logging.StreamHandler()
_console.setFormatter(_fmt)
_file = RotatingFileHandler(os.path.join(LOG_DIR, "notification_service.log"), maxBytes=5_000_000, backupCount=3)
_file.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_console, _file])
logger = logging.getLogger("notification_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    for _ in range(5):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            break
        except Exception:
            await asyncio.sleep(1)
    consumer_task = asyncio.create_task(start_kafka_consumer())
    logger.info("Notification service started successfully")
    yield
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Notification Service", lifespan=lifespan)
app.add_exception_handler(AppException, app_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notification_routes.router)
app.include_router(ws_routes.router)


@app.get("/health")
async def health():
    try:
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error("Health check DB failure: %s", e)
        db_status = "disconnected"
    return {"service": "notification", "status": "ok" if db_status == "connected" else "degraded", "db": db_status}