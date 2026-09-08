from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService

router = APIRouter()


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    authors: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """
    Upload and ingest a PDF document.
    Extracts text preserving page boundaries and creates source-aware chunks.
    """
    service = DocumentService(db)
    return await service.upload_and_process(file=file, title=title, authors=authors)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """List all indexed documents with processing status."""
    service = DocumentService(db)
    return await service.list_documents()


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    """Get detailed document metadata, extracted pages, and generated chunks."""
    service = DocumentService(db)
    return await service.get_document(document_id)


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a document and purge all derived pages, chunks, and storage files."""
    service = DocumentService(db)
    return await service.delete_document(document_id)
