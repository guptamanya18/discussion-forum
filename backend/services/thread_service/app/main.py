import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler
import sqlalchemy
from contextlib import asynccontextmanager
from fastapi import FastAPI

# logs go to console

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
_fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")

# logs also go to file
_console = logging.StreamHandler()
_console.setFormatter(_fmt)

# file rotates after 5MB -- prevents huge files
_file = RotatingFileHandler(os.path.join(LOG_DIR, "thread_service.log"), maxBytes=5_000_000, backupCount=3)
_file.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_console, _file])
logger = logging.getLogger("thread_service")

from app.database import engine, Base
from app.models import user, thread, like  # noqa: F401
from app.models import report as report_model  # noqa: F401 # unused import warning being ignored
from app.routes import thread_routes, report_routes
from app.kafka_producer import kafka_producer  # sends events like notifications
from app.kafka_consumer import start_kafka_consumer  # listens to events ( from other services )
from app.core.exceptions import AppException, app_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    for _ in range(5):

        # credate all tables if not exists and retry 5 times in case db is not ready
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.execute(
                    sqlalchemy.text( 
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar VARCHAR DEFAULT NULL"   # migration -- add avatar col if not availab;e
                    )
                )
            break
        except Exception:
            await asyncio.sleep(1)
    await kafka_producer.start()

    # runs consumer in background thread -- keeps listening for events
    consumer_task = asyncio.create_task(start_kafka_consumer())
    logger.info("Thread service started successfully")
    yield

    # shut down begins after yield
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await kafka_producer.stop()


app = FastAPI(title="Thread Service", lifespan=lifespan)

app.add_exception_handler(AppException, app_exception_handler)

# attaches all endpoints to app
app.include_router(thread_routes.router)
app.include_router(report_routes.router)


@app.get("/health")
async def health():
    try:
        async with engine.connect() as conn:

            # if db works -- connected else disconnected
            await conn.execute(sqlalchemy.text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error("Health check DB failure: %s", e)
        db_status = "disconnected"
    kafka_status = "connected" if kafka_producer._producer else "disconnected"
    return {"service": "thread", "status": "ok" if db_status == "connected" else "degraded", "db": db_status, "kafka": kafka_status}