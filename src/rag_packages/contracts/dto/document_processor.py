from typing import Any, Literal, TypeAlias
from pydantic import Field
from rag_packages.contracts.dto.shared_dto import BaseDTO
# from docling_core.types.doc import TableItem, PictureItem, BoundingBox


FileType = Literal[
    "pdf", "docx", "doc", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "bmp", "csv", ""
]
FILE_TYPES = {"pdf", "docx", "doc", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "bmp", "csv", ""}


ChunkStrategy: TypeAlias = Literal["docling", "markdown"]

class ChunkDetails(BaseDTO):
    pages: list[int] | None = Field(default_factory=list)
    headings: list[str] | None = Field(default_factory=list)
    captions: list[str] | None = Field(default_factory=list)
    tables: list[dict] | None = Field(default_factory=list)  # TableItem
    figures: list[dict] | None = Field(default_factory=list)  # PictureItem
    bbox: list[dict] | None = Field(default_factory=list)  # BoundingBox


class ProcessedChunk(BaseDTO):
    index: int
    text: str
    details: ChunkDetails | None = None
    metadata: dict[str, Any] | None = None


class ProcessedDocument(BaseDTO):
    file_name: str | None = None
    file_type: FileType
    markdown: str
    chunks: list[ProcessedChunk]
