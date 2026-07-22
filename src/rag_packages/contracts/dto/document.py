from datetime import datetime
from typing import Any
from rag_packages.contracts.dto.shared_dto import BaseDTO, APIResponse, APIListResponse
from rag_packages.contracts.types.shared_types import DocSource, IngestStatus


class CreateDocumentRequest(BaseDTO):
    name: str
    file_url: str
    library_name: str | None = None
    library_id: str | None = None
    site_url: str
    parent_folder_path: str | None = None
    source: DocSource
    file_metadata: dict[str, Any] | None = None
    last_modified: datetime
    file_type: str
    file_mime_type: str | None = None
    file_size: int | None = None

    ingest_initiated_at: datetime | None = None
    ingest_status: IngestStatus | None = None
    prev_batch_ingest_init: datetime | None = None


class UpdateDocumentRequest(BaseDTO):
    name: str | None = None
    library_name: str | None = None
    library_id: str | None = None
    site_url: str | None = None
    parent_folder_path: str | None = None
    source: DocSource | None = None
    file_metadata: dict[str, Any] | None = None
    last_modified: datetime | None = None
    file_type: str | None = None
    file_mime_type: str | None = None
    file_size: int | None = None

    ingest_initiated_at: datetime | None = None
    ingest_status: IngestStatus | None = None
    prev_batch_ingest_init: datetime | None = None


class DocumentResponse(BaseDTO):
    id: int
    name: str
    file_url: str
    library_name: str | None = None
    library_id: str | None = None
    site_url: str
    parent_folder_path: str | None = None
    source: DocSource
    file_metadata: dict[str, Any] | None = None
    last_modified: datetime
    file_type: str
    file_mime_type: str | None = None
    file_size: int | None = None

    # not stored in db, may be added in response for single document retrieval
    file_b64: str | None = None
    file_sha256: str | None = None

    ingest_initiated_at: datetime | None = None
    ingest_status: IngestStatus | None = None
    prev_batch_ingest_init: datetime | None = None

    created_at: datetime
    created_by_id: int | None = None
    updated_at: datetime | None = None
    updated_by_id: int | None = None
    is_active: bool
    is_deleted: bool


class DocumentAPIResponse(APIResponse):
    data: DocumentResponse | None = None


class DocumentListAPIResponse(APIListResponse):
    data: list[DocumentResponse] | None = None
