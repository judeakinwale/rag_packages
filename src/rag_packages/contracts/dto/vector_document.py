from datetime import datetime
from typing import Any
from rag_packages.contracts.dto.document_processor import ChunkDetails
from rag_packages.contracts.dto.shared_dto import BaseDTO, APIResponse, APIListResponse
from rag_packages.contracts.types.shared_types import DocSource


class VectorDocumentFileMetadata(BaseDTO):
    source: DocSource
    file_url: str
    library_name: str | None = None
    file_type: str
    file_mime_type: str | None = None
    file_size: int | None = None
    last_modified: datetime


class CreateVectorDocumentRequest(BaseDTO):
    doc_id: int  # id of the related document from the ingest service
    chunk_id: int | None = None
    file_name: str
    text: str
    details: ChunkDetails
    metadata: dict[str, Any] | None = None
    file_metadata: VectorDocumentFileMetadata
    initiated_at: datetime | None = None


class VectorDocumentPayload(CreateVectorDocumentRequest):
    pass


class UpdateVectorDocumentRequest(BaseDTO):
    doc_id: int
    chunk_id: int | None = None
    file_name: str | None = None
    text: str | None = None
    details: ChunkDetails
    metadata: dict[str, Any] | None = None
    file_metadata: VectorDocumentFileMetadata | None = None

    id: int | str | None = None


class VectorDocumentResponse(BaseDTO):
    doc_id: int
    chunk_id: int
    file_name: str
    text: str
    details: ChunkDetails
    metadata: dict[str, Any] | None = None
    file_metadata: VectorDocumentFileMetadata | None = None

    initiated_at: datetime | None = None
    completed_at: datetime | None = None
    is_active: bool | None = None
    is_deleted: bool | None = None


class VectorDocumentFileMetadataJSON(VectorDocumentFileMetadata):
    last_modified: datetime | int | None = None  # timestamp in ms (13 digit int)


class VectorDocumentResponseJSON(VectorDocumentResponse):
    file_metadata: VectorDocumentFileMetadataJSON | None = None

    # only for use to add details to the response dict for assistant usage
    details_dict: dict[str, Any] | None = None
    details_markdown: str | None = None

    initiated_at: datetime | int | None = None  # timestamp in ms (13 digit int)
    completed_at: datetime | int | None = None  # timestamp in ms (13 digit int)


class DocumentAPIResponse(APIResponse):
    data: VectorDocumentResponse | None = None


class VectorDocumentListAPIResponse(APIListResponse):
    data: list[VectorDocumentResponse] | None = None
