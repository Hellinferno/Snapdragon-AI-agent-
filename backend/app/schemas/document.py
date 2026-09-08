from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    page_number: int
    text: str
    ocr_used: bool


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    page_id: str
    page_number: int | None = None
    chunk_index: int
    text: str
    section: str | None = None
    embedding_id: str | None = None


class DocumentCreate(BaseModel):
    title: str | None = None
    authors: str | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    title: str | None = None
    authors: str | None = None
    created_at: datetime
    status: str
    page_count: int
    file_size: int
    chunk_count: int = 0
    error_message: str | None = None


class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    status: str
    message: str


class DocumentDetailResponse(DocumentResponse):
    pages: list[PageResponse] = []
    chunks: list[ChunkResponse] = []
