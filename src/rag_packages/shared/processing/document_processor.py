import asyncio
import base64
import binascii
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
import tiktoken
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.openai import (
    OpenAITokenizer,
    BaseTokenizer,
)

# from transformers import AutoTokenizer
from docling.datamodel.base_models import ConversionStatus
from docling.document_converter import DocumentConverter
from docling_core.types.doc import DoclingDocument, TableItem, PictureItem, BoundingBox
from docling_core.transforms.chunker import DocChunk
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_core.documents import Document as LangChainDocument
from rag_packages.contracts.dto.document_processor import (
    FileType,
    FILE_TYPES,
    ChunkStrategy,
    ChunkDetails,
    ProcessedChunk,
    ProcessedDocument,
)


logger = logging.getLogger(__name__)


class InvalidFileError(ValueError):
    """Raised when the provided file is invalid or unsupported."""

    pass


class DocumentProcessor:
    def __init__(
        self,
        header_splitter: MarkdownHeaderTextSplitter | None = None,
        char_splitter: RecursiveCharacterTextSplitter | None = None,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        max_file_size: int = 10 * 1024 * 1024,  # 10 MB in bytes
        tokenizer: BaseTokenizer | None = None,
    ):
        self._lock = asyncio.Lock()
        self.converter: DocumentConverter | None = None
        self.header_splitter = header_splitter
        self.char_splitter = char_splitter
        self._max_file_size = max_file_size
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._tokenizer = tokenizer

    async def _get_converter(self) -> DocumentConverter:
        # TODO: Verify DocumentConverter.convert() is safe for concurrent calls on the same instance.
        # If not, either:
        # - serialize convert() with a lock, or
        # - create a new instance of DocumentConverter for each request,
        #   using one converter per worker/request, while being
        #   mindful of the expensive converter init.
        if self.converter is not None:
            return self.converter

        async with self._lock:
            if self.converter is not None:
                return self.converter

            self.converter = await asyncio.to_thread(DocumentConverter)

        return self.converter

    def _get_tokenizer(self) -> OpenAITokenizer:
        if self._tokenizer is not None:
            return self._tokenizer

        # tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        tokenizer = OpenAITokenizer(
            tokenizer=tiktoken.encoding_for_model("gpt-4o"), max_tokens=1024
        )
        return tokenizer

    def _get_chunker(self) -> HybridChunker:
        tokenizer = self._get_tokenizer()

        chunker = HybridChunker(tokenizer=tokenizer)
        return chunker

    def _get_splitters(
        self, **kwargs
    ) -> tuple[MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter]:

        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            # ("####", "Header 4"),
        ]
        header_splitter = self.header_splitter or MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on, **kwargs
        )

        char_splitter = self.char_splitter or RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            # the first two separators are for headings and in this case, redundant
            separators=["\n# ", "\n## ", "\n\n", "\n", " ", ""],
        )

        return header_splitter, char_splitter

    def _get_file_binary(self, file_b64: str) -> bytes:
        try:
            decoded = base64.b64decode(file_b64, validate=True)

            if len(decoded) > self._max_file_size:
                raise InvalidFileError(
                    f"File too large; expected less than {self._max_file_size} bytes."
                )

            return decoded

        except InvalidFileError as e:
            raise InvalidFileError(f"Invalid file provided: {e}") from e

        except (binascii.Error, ValueError) as e:
            raise ValueError(f"Invalid base64 input: {e}") from e

    def _create_temporary_file(self, file: bytes, file_type: FileType) -> Path:
        if file_type not in FILE_TYPES:
            raise ValueError(f"Unsupported file type: {file_type}")

        with NamedTemporaryFile(
            mode="wb", delete=False, suffix=f".{file_type}"
        ) as temp_file:
            temp_file.write(file)
            return Path(temp_file.name)

    def _remove_temporary_file(self, path: Path):
        try:
            path.unlink(missing_ok=True)
            # os.remove(path)
        except Exception:
            logger.exception("Error removing temporary file")

    def _get_processed_langchain_md_chunk_with_metadata(
        self, doc: LangChainDocument, index: int
    ) -> ProcessedChunk:
        metadata = doc.metadata

        # sort specifically for header keys
        # use natsorted if sorting is inconsistent
        headings = [
            v
            for key, v in sorted(metadata.items())
            if isinstance(key, str) and key.startswith("Header") and v is not None
        ]
        details = ChunkDetails(headings=headings)
        return ProcessedChunk(
            index=index,
            text=doc.page_content,
            details=details,
            metadata=metadata,
        )

    def _get_processed_doc_chunk_with_metadata(
        self, chunk: DocChunk, index: int
    ) -> ProcessedChunk:
        details = self.get_doc_chunk_details(chunk)
        metadata = chunk.meta.model_dump(
            exclude={"doc_items", "headings"},
            exclude_unset=True,
            exclude_none=True,
        )
        return ProcessedChunk(
            index=index,
            text=chunk.text,
            details=details,
            metadata=metadata,
        )

    @staticmethod
    def get_doc_chunk_details(chunk: DocChunk) -> ChunkDetails:
        doc_items = chunk.meta.doc_items
        headings = chunk.meta.headings
        captions = chunk.meta.captions

        tables: list[TableItem] = []
        figures: list[PictureItem] = []
        pages_set: set[int] = set()
        bbox: list[BoundingBox] = []

        for item in doc_items:
            if isinstance(item, TableItem):
                tables.append(item)

            elif isinstance(item, PictureItem):
                figures.append(item)

            for prov_item in item.prov:
                prov_page_no = prov_item.page_no
                prov_bbox = prov_item.bbox
                pages_set.add(prov_page_no)
                bbox.append(prov_bbox)

        pages = sorted(pages_set)
        # if pages:
        #     logger.debug(
        #         f"chunk headings and page: {headings}, {pages[0]} - {pages[-1]}"
        #     )

        details = ChunkDetails(
            pages=pages,
            headings=headings,
            captions=captions,
            tables=tables,
            figures=figures,
            bbox=bbox,
        )
        return details

    async def extract_text(
        self,
        file_b64: str,
        file_type: FileType,
        # file_name: str | None = None,
    ) -> tuple[str, DoclingDocument]:
        file_path: Path | None = None
        try:
            file_binary = self._get_file_binary(file_b64)
            file_path = self._create_temporary_file(file_binary, file_type)

            converter = await self._get_converter()
            result = await asyncio.to_thread(converter.convert, file_path)

            if result.status == ConversionStatus.FAILURE:
                raise ValueError(
                    f"Document conversion failed: {', '.join(result.errors)}"
                )

            document = result.document
            markdown = document.export_to_markdown()

            return markdown, document

        finally:
            if file_path is not None:
                self._remove_temporary_file(file_path)

    def chunk_text(
        self,
        text: str,
    ) -> list[ProcessedChunk]:
        header_splitter, char_splitter = self._get_splitters()

        header_chunks = header_splitter.split_text(text)
        chunks = char_splitter.split_documents(header_chunks)

        processed_chunks = [
            self._get_processed_langchain_md_chunk_with_metadata(chunk, i)
            for i, chunk in enumerate(chunks)
        ]
        return processed_chunks

    def chunk_document(
        self,
        document: DoclingDocument,
    ) -> list[ProcessedChunk]:
        chunker = self._get_chunker()
        chunks = chunker.chunk(document)

        processed_chunks = [
            self._get_processed_doc_chunk_with_metadata(chunk, i)
            for i, chunk in enumerate(chunks)
        ]
        return processed_chunks

    async def process(
        self,
        file_b64: str,
        file_type: FileType,
        file_name: str | None = None,
        chunk_strategy: ChunkStrategy = "docling",
    ) -> ProcessedDocument:

        text, document = await self.extract_text(file_b64, file_type)

        processed_chunks: list[ProcessedChunk]
        match chunk_strategy:
            case "docling":
                processed_chunks = await asyncio.to_thread(
                    self.chunk_document, document
                )
            case "markdown":
                processed_chunks = await asyncio.to_thread(self.chunk_text, text)
            case _:
                raise ValueError(f"Invalid chunk strategy: {chunk_strategy}")

        return ProcessedDocument(
            file_name=file_name,
            file_type=file_type,
            markdown=text,
            chunks=processed_chunks,
        )
