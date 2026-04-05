import json
import logging

from aiokafka import AIOKafkaProducer
from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaProducerWrapper:
    def __init__(self):
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await self._producer.start()
            logger.info("Kafka producer started")
        except Exception as e:
            logger.error("Failed to start Kafka producer: %s", e)
            self._producer = None

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def send(self, topic: str, value: dict):
        if self._producer is None:
            logger.warning("Kafka producer not started, dropping message")
            return
        try:
            await self._producer.send_and_wait(topic, value)
            logger.info("Sent to %s: %s", topic, value)
        except Exception as e:
            logger.error("Failed to send to Kafka: %s", e)


kafka_producer = KafkaProducerWrapper()
