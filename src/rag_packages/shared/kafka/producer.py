import json
import logging
from typing import Any
from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(
        self,
        bootstrap_servers: str = "kafka:9092",
        service_name: str = None,
        overrides: dict[str, Any] | None = None,
    ):
        valid_overrides = overrides or {}
        self._producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retry_backoff_ms=500,
            request_timeout_ms=1000,
            acks="all",
            **valid_overrides,
        )
        self._started = False
        self.service_name = service_name

    @property
    def producer(self) -> AIOKafkaProducer:
        return self._producer
    
    @property
    def started(self) -> bool:
        return self._started

    async def start(self) -> AIOKafkaProducer:
        await self._producer.start()
        self._started = True
        return self._producer

    async def stop(self):
        await self._producer.stop()
        self._started = False

    async def publish(self, topic: str, message: dict, key: str = None):
        try:
            if not self._started:
                raise RuntimeError("Producer has not been started")

            await self._producer.send_and_wait(
                topic, message, key.encode() if key else None
            )
        except Exception:
            logger.exception(
                f"[{self.service_name}] Error publishing message to topic {topic}"
            )
            raise
