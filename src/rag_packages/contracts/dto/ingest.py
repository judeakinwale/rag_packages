from datetime import datetime
from rag_packages.contracts.dto.shared_dto import BaseDTO, APIResponse
from rag_packages.contracts.dto.document import DocumentResponse


# NOTE: library_ids is optional because it is only relevant for sharepoint and
# if none if provided for sharepoint, it gets all documents from all libraries


class CreateIngestRequest(BaseDTO):
    library_ids: list[str] | None = None
    # process newly modified documents and reprocess tracked documents from the last ingest batch
    force_reprocess: bool = False
    # process newly modified documents and reprocess all documents
    force_reprocess_all: bool = False


class CompleteIngestRequest(BaseDTO):
    library_ids: list[str] | None = None
    document_ids: list[int]
    ingest_initiated_at: datetime


class IngestResponse(BaseDTO):
    library_ids: list[str] | None = None
    documents: list[DocumentResponse]


class IngestAPIResponse(APIResponse):
    data: IngestResponse | None = None
