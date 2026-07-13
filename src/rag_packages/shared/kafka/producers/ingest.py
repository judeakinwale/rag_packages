from rag_packages.shared.kafka.producer import KafkaProducer
from rag_packages.contracts.events.ingest import (
    IngestCompletedEvent,
    IngestStartedEvent,
    ProcessingStartedEvent,
    ProcessingCompletedEvent,
    ProcessingFailedEvent,
)


class IngestProducer:
    def __init__(self, producer: KafkaProducer):
        self.producer = producer

    async def test(self, event: dict, key: str | None = None):
        await self.producer.publish(
            "test.topic",
            event,
            key,
        )

    async def ingest_started(self, event: IngestStartedEvent, key: str | None = None):
        await self.producer.publish(
            "ingest.started",
            event.model_dump(),
            key,
        )

    async def processing_started(
        self, event: ProcessingStartedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "ingest.processing",
            event.model_dump(),
            key,
        )

    async def processing_completed(
        self, event: ProcessingCompletedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "ingest.processing.completed",
            event.model_dump(),
            key,
        )

    async def processing_failed(
        self, event: ProcessingFailedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "ingest.processing.failed",
            event.model_dump(),
            key,
        )

    async def ingest_completed(
        self, event: IngestCompletedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "ingest.completed",
            event.model_dump(),
            key,
        )
