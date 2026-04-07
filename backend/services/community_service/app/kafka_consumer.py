import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer
from sqlalchemy import select

from app.core.config import settings
from app.database import AsyncSessionLocal
from app.models.user import User

logger = logging.getLogger("community_service.consumer")


async def start_kafka_consumer():
    consumer = AIOKafkaConsumer(
        "user-events",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="community-service-user-sync",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
    )

    while True:
        try:
            await consumer.start()
            logger.info("Kafka consumer started, listening for user-events")
            break
        except Exception as e:
            logger.warning("Kafka not ready, retrying in 3s: %s", e)
            await asyncio.sleep(3)

    try:
        async for msg in consumer:
            event = msg.value
            event_type = event.get("type")
            if event_type not in ("user_created", "user_updated"):
                continue

            user_id = event.get("user_id")
            if not user_id:
                continue

            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalars().first()
                if user:
                    user.username = event["username"]
                    user.email = event["email"]
                    user.role = event.get("role", "member")
                    user.avatar = event.get("avatar")
                    user.is_active = 1 if event.get("is_active", True) else 0
                    await db.commit()
                    logger.info("Updated user %d from Kafka event", user_id)
                elif event_type == "user_created":
                    new_user = User(
                        id=user_id,
                        username=event["username"],
                        email=event["email"],
                        role=event.get("role", "member"),
                        avatar=event.get("avatar"),
                        is_active=1 if event.get("is_active", True) else 0,
                        hashed_password="synced",
                    )
                    db.add(new_user)
                    await db.commit()
                    logger.info("Created user %d from Kafka event", user_id)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")
