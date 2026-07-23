from datetime import datetime
from typing import Any
from pydantic import Field
from rag_packages.contracts.dto.shared_dto import BaseDTO, APIResponse, APIListResponse

from rag_packages.contracts.dto.document_processor import ProcessedChunk
from rag_packages.contracts.dto.document import DocumentResponse
from rag_packages.contracts.dto.vector_document import VectorDocumentResponse


class SimpleChat(BaseDTO):
    prompt: str
    response: str | None = None


# Primarily used for adding references to an assistant response on the chat / prompt endpoints
class ChatMessageReferences(BaseDTO):
    document_chunks: list[ProcessedChunk] = Field(default_factory=list)
    vector_documents: list[VectorDocumentResponse] = Field(default_factory=list)
    documents: list[DocumentResponse] = Field(default_factory=list)


class ChatMessage(BaseDTO):
    role: str
    content: str | list[dict[str, Any]]
    timestamp: datetime
    references: ChatMessageReferences | None = None


class OpenAIChatMessage(BaseDTO):
    role: str
    content: str | list[dict[str, Any]]


# For working with a prompt sent by the user
class AddPromptRequest(BaseDTO):
    prompt: str
    file_url: str | None = None
    b64_file: str | None = None
    file_type: str | None = None
    file_mime_type: str | None = None
    email: str | None = None
    session_id: str | None = None
    site_url: str | None = None
    timestamp: datetime | None = None


class CreateChatRequest(BaseDTO):
    email: str
    messages: list[ChatMessage] = Field(default_factory=list)
    session_id: str | None = None
    site_url: str | None = None


class UpdateChatRequest(BaseDTO):
    email: str | None = None
    # messages to replace the existing messages
    messages: list[ChatMessage] = Field(default_factory=list)
    # new messages to be appended to the existing messages
    new_messages: list[ChatMessage] = Field(default_factory=list)
    session_id: str | None = None
    site_url: str | None = None


class ChatResponse(BaseDTO):
    id: int

    email: str
    messages: list[ChatMessage]
    session_id: str | None = None
    site_url: str | None = None

    created_at: datetime
    created_by_id: int | None = None
    updated_at: datetime | None = None
    updated_by_id: int | None = None
    is_active: bool
    is_deleted: bool


class ChatAPIResponse(APIResponse):
    data: ChatResponse | None = None


class ChatListAPIResponse(APIListResponse):
    data: list[ChatResponse] | None = None
