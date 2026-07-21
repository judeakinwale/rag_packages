from rag_packages.shared.kafka.producer import KafkaProducer
from rag_packages.contracts.events.ingest import (
    IngestCompletedEvent,
    IngestStartedEvent,
    ProcessingStartedEvent,
    ProcessingCompletedEvent,
    ProcessingFailedEvent,
)
from rag_packages.shared.utils.format import get_date_iso_str


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

        data = event.model_dump()
        data["ingest_initiated_at"] = get_date_iso_str(event.ingest_initiated_at)

        await self.producer.publish(
            "ingest.processing.completed",
            data,
            key,
        )

    async def processing_failed(
        self, event: ProcessingFailedEvent, key: str | None = None
    ):

        data = event.model_dump()
        data["ingest_initiated_at"] = get_date_iso_str(event.ingest_initiated_at)
        data["ingest_failed_at"] = get_date_iso_str(event.ingest_failed_at)

        await self.producer.publish(
            "ingest.processing.failed",
            data,
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
