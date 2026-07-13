from enum import StrEnum


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class DocSource(StrEnum):
    LOCAL = "local"
    SHAREPOINT = "sharepoint"
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"
    OTHER = "other"


class IngestStatus(StrEnum):
    STARTED = "started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
