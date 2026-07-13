from typing import Any, Literal, TypeAlias
from pydantic import Field
from docling_core.types.doc import TableItem, PictureItem, BoundingBox

from rag_packages.contracts.dto.shared_dto import BaseDTO


FileType = Literal[
    "pdf", "docx", "doc", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "bmp"
]
FILE_TYPES = {"pdf", "docx", "doc", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "bmp"}


ChunkStrategy: TypeAlias = Literal["docling", "markdown"]


class ChunkDetails(BaseDTO):
    pages: list[int] = Field(default_factory=list)
    headings: list[str] = Field(default_factory=list)
    captions: list[str] = Field(default_factory=list)
    tables: list[TableItem] = Field(default_factory=list)
    figures: list[PictureItem] = Field(default_factory=list)
    bbox: list[BoundingBox] = Field(default_factory=list)


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
