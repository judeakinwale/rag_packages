from datetime import datetime
from rag_packages.contracts.dto.document import DocSource
from rag_packages.contracts.events.shared_events import BaseEvent


class IngestStartedEvent(BaseEvent):
    document_ids: list[int]
    source: DocSource


# track processing for each document, when all documents are processed, emit IngestCompletedEvent
class ProcessingStartedEvent(BaseEvent):
    # ?? for tracking and calling ingest_completed (not sure this is useful)
    document_ids: list[int] | None = None
    document_id: int
    source: DocSource
    remaining_documents: int


class ProcessingCompletedEvent(BaseEvent):
    library_id: str | None = None
    document_id: int
    source: DocSource | None = None
    remaining_documents: int | None = None
    ingest_initiated_at: datetime


class ProcessingFailedEvent(ProcessingCompletedEvent):
    error: str | None = None
    detailed_error: str | None = None
    ingest_initiated_at: datetime | None = None
    ingest_failed_at: datetime


class IngestCompletedEvent(IngestStartedEvent):
    pass
