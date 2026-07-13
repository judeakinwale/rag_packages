from datetime import datetime
from rag_packages.contracts.types.shared_types import DocSource
from rag_packages.contracts.events.shared_events import BaseEvent


class DocumentCreatedEvent(BaseEvent):
    id: int
    name: str
    file_url: str
    source: DocSource
    ingest_initiated_at: datetime
    # ? consider adding more fields from CreateDocumentRequest


class DocumentProcessedEvent(DocumentCreatedEvent):
    file_metadata: dict | None = None


class DocumentUpdatedEvent(DocumentCreatedEvent):
    updated: list[str] | None = None  # list of updated fields


class DocumentSoftDeletedEvent(DocumentCreatedEvent):
    pass


class DocumentDeletedEvent(DocumentCreatedEvent):
    pass
