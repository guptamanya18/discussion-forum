import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer
from sqlalchemy import select

from app.core.config import settings
from app.database import AsyncSessionLocal
from app.models.notification import Notification
from app.models.user import User
from app.ws_manager import manager

logger = logging.getLogger(__name__)

TOPICS = ["thread-events", "comment-events", "community-events", "user-events"]


async def start_kafka_consumer():
    """
    Long-running coroutine that consumes events from Kafka topics
    and creates notifications in the database + pushes via WebSocket.
    """
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="notification-service",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
    )

    # Retry loop — Kafka may not be ready when this service starts
    while True:
        try:
            await consumer.start()
            logger.info("Kafka consumer started, subscribed to %s", TOPICS)
            break
        except Exception as e:
            logger.warning("Kafka not ready, retrying in 3s: %s", e)
            await asyncio.sleep(3)

    try:
        async for msg in consumer:
            event = msg.value
            logger.info("Received event from %s: %s", msg.topic, event)

            # Broadcast events — no DB save, just push to all clients
            if event.get("broadcast"):
                broadcast_data = {"type": event.get("type")}
                # Like updates
                if event.get("thread_id"):
                    broadcast_data["thread_id"] = event["thread_id"]
                if event.get("comment_id"):
                    broadcast_data["comment_id"] = event["comment_id"]
                if event.get("like_count") is not None:
                    broadcast_data["like_count"] = event["like_count"]
                if event.get("deleted_count") is not None:
                    broadcast_data["deleted_count"] = event["deleted_count"]
                # New thread/comment data
                if event.get("thread"):
                    broadcast_data["thread"] = event["thread"]
                if event.get("comment"):
                    broadcast_data["comment"] = event["comment"]
                # Edit data
                if event.get("title") is not None:
                    broadcast_data["title"] = event["title"]
                if event.get("description") is not None:
                    broadcast_data["description"] = event["description"]
                if event.get("tags") is not None:
                    broadcast_data["tags"] = event["tags"]
                if event.get("content") is not None:
                    broadcast_data["content"] = event["content"]
                if event.get("avatar") is not None:
                    broadcast_data["avatar"] = event["avatar"]
                if event.get("user_id") is not None:
                    broadcast_data["user_id"] = event["user_id"]
                await manager.broadcast(broadcast_data)
                continue

            # User update events — sync local user copy, not a notification
            if event.get("type") == "user_updated":
                uid = event.get("user_id")
                if uid:
                    async with AsyncSessionLocal() as session:
                        result = await session.execute(
                            select(User).where(User.id == uid)
                        )
                        user = result.scalars().first()
                        if user:
                            user.username = event["username"]
                            user.email = event["email"]
                            user.role = event.get("role", "member")
                            user.avatar = event.get("avatar")
                            user.is_active = 1 if event.get("is_active", True) else 0
                            await session.commit()
                            logger.info("Synced user %d from Kafka event", uid)
                continue

            user_id = event.get("user_id")
            ntype = event.get("type", "general")
            message = event.get("message", "")
            reference_id = event.get("reference_id")

            if not user_id:
                continue

            # 1. Save to database
            async with AsyncSessionLocal() as session:
                notif = Notification(
                    user_id=user_id,
                    type=ntype,
                    message=message,
                    reference_id=reference_id,
                )
                session.add(notif)
                await session.commit()
                await session.refresh(notif)

            # 2. Push via WebSocket (real-time)
            await manager.send_to_user(user_id, {
                "id": notif.id,
                "type": ntype,
                "message": message,
                "reference_id": reference_id,
                "actor_id": event.get("actor_id"),
                "is_read": False,
                "created_at": str(notif.created_at),
            })
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")