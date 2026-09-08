import hashlib
import os
import re
from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import logger
from app.models.db_models import Chunk, Document, Page
from app.providers.embedding_provider import embedding_provider
from app.providers.vector_store import SQLiteVectorStore
from app.schemas.document import (
    ChunkResponse,
    DocumentDetailResponse,
    DocumentResponse,
    DocumentUploadResponse,
    PageResponse,
)
from app.services.chunker import chunk_pages
from app.services.pdf_parser import parse_pdf


def sanitize_filename(filename: str) -> str:
    """Sanitizes filename against directory traversal and illegal characters."""
    clean = re.sub(r"[^\w\s\.-]", "_", Path(filename).name)
    return clean[:200] or "unnamed_document.pdf"


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload_and_process(
        self,
        file: UploadFile,
        title: str | None = None,
        authors: str | None = None,
    ) -> DocumentUploadResponse:
        """
        Validates, saves, extracts, and indexes a PDF document.
        Preserves page boundaries and records chunks in SQLite.
        """
        filename = sanitize_filename(file.filename or "document.pdf")
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF documents are supported.",
            )

        # Read content to compute hash and check size
        content = await file.read()
        return await self._process_raw_bytes(content, filename, title, authors)

    async def process_local_pdf(
        self,
        pdf_path: Path,
        title: str | None = None,
        authors: str | None = None,
    ) -> DocumentUploadResponse:
        """Process a local PDF directly from disk without multipart upload."""
        if not pdf_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Local PDF file {pdf_path.name} not found.",
            )
        content = pdf_path.read_bytes()
        return await self._process_raw_bytes(content, pdf_path.name, title, authors)

    async def _process_raw_bytes(
        self,
        content: bytes,
        filename: str,
        title: str | None = None,
        authors: str | None = None,
    ) -> DocumentUploadResponse:
        """Core parsing and indexing pipeline for raw PDF bytes."""
        file_size = len(content)
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        if file_size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
            )

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        content_hash = hashlib.sha256(content).hexdigest()

        # Check for duplicate document
        existing = await self.db.scalar(
            select(Document).where(Document.content_hash == content_hash)
        )
        if existing:
            return DocumentUploadResponse(
                id=existing.id,
                filename=existing.filename,
                status=existing.status,
                message="Document already uploaded and processed.",
            )

        # Save file to disk
        safe_stored_name = f"{content_hash[:12]}_{filename}"
        stored_path = settings.UPLOAD_DIR / safe_stored_name

        try:
            with open(stored_path, "wb") as f:
                f.write(content)
        except OSError as e:
            logger.error("Failed to write document to disk: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store uploaded document.",
            )

        # Create initial Document record
        doc = Document(
            filename=filename,
            title=title or filename.rsplit(".", 1)[0].replace("_", " ").title(),
            authors=authors,
            content_hash=content_hash,
            file_path=str(stored_path),
            file_size=file_size,
            status="PROCESSING",
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)

        # Process document (parse & chunk)
        try:
            parsed = parse_pdf(stored_path)
            doc.page_count = parsed.page_count
            if not doc.title and parsed.title:
                doc.title = parsed.title
            if not doc.authors and parsed.authors:
                doc.authors = parsed.authors

            # Save pages
            page_map: dict[int, Page] = {}
            for parsed_page in parsed.pages:
                page = Page(
                    document_id=doc.id,
                    page_number=parsed_page.page_number,
                    text=parsed_page.text,
                    ocr_used=parsed_page.ocr_used,
                )
                self.db.add(page)
                page_map[parsed_page.page_number] = page

            # Flush so pages receive their generated IDs
            await self.db.flush()

            # Generate chunks
            generated_chunks = chunk_pages(
                pages=parsed.pages,
                chunk_size=settings.CHUNK_SIZE_CHARS,
                chunk_overlap=settings.CHUNK_OVERLAP_CHARS,
            )

            created_chunks: list[Chunk] = []
            for gen_chunk in generated_chunks:
                parent_page = page_map.get(gen_chunk.page_number)
                if not parent_page:
                    continue

                chunk = Chunk(
                    document_id=doc.id,
                    page_id=parent_page.id,
                    chunk_index=gen_chunk.chunk_index,
                    text=gen_chunk.text,
                    section=gen_chunk.section,
                )
                self.db.add(chunk)
                created_chunks.append(chunk)

            # Flush to obtain generated chunk IDs
            await self.db.flush()

            # Generate and persist embeddings in vector store
            if created_chunks:
                chunk_texts = [c.text for c in created_chunks]
                vectors = await embedding_provider.embed_batch(chunk_texts)
                vector_entries = [
                    (c.id, doc.id, vec) for c, vec in zip(created_chunks, vectors, strict=False)
                ]
                vector_store = SQLiteVectorStore(self.db)
                await vector_store.add_vectors(vector_entries)

            doc.status = "INDEXED"
            await self.db.commit()
            logger.info("Successfully indexed document %s (%d pages, %d chunks)", doc.id, doc.page_count, len(generated_chunks))

        except Exception as err:
            logger.error("Error processing document %s: %s", doc.id, str(err), exc_info=True)
            doc.status = "FAILED"
            doc.error_message = str(err)
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Document parsing failed: {str(err)}",
            )

        return DocumentUploadResponse(
            id=doc.id,
            filename=doc.filename,
            status=doc.status,
            message="Document successfully processed and indexed.",
        )

    async def list_documents(self) -> list[DocumentResponse]:
        """Lists all documents with chunk counts."""
        stmt = (
            select(
                Document,
                func.count(Chunk.id).label("chunk_count"),
            )
            .outerjoin(Chunk, Chunk.document_id == Document.id)
            .group_by(Document.id)
            .order_by(Document.created_at.desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        docs: list[DocumentResponse] = []
        for doc, chunk_count in rows:
            docs.append(
                DocumentResponse(
                    id=doc.id,
                    filename=doc.filename,
                    title=doc.title,
                    authors=doc.authors,
                    created_at=doc.created_at,
                    status=doc.status,
                    page_count=doc.page_count,
                    file_size=doc.file_size,
                    chunk_count=chunk_count or 0,
                    error_message=doc.error_message,
                )
            )
        return docs

    async def get_document(self, document_id: str) -> DocumentDetailResponse:
        """Retrieves a document with full page and chunk details."""
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(
                selectinload(Document.pages),
                selectinload(Document.chunks).selectinload(Chunk.page),
            )
        )
        doc = await self.db.scalar(stmt)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found.",
            )

        pages_resp = [
            PageResponse(
                id=p.id,
                document_id=p.document_id,
                page_number=p.page_number,
                text=p.text,
                ocr_used=p.ocr_used,
            )
            for p in doc.pages
        ]

        chunks_resp = [
            ChunkResponse(
                id=c.id,
                document_id=c.document_id,
                page_id=c.page_id,
                page_number=c.page.page_number if c.page else None,
                chunk_index=c.chunk_index,
                text=c.text,
                section=c.section,
                embedding_id=c.embedding_id,
            )
            for c in doc.chunks
        ]

        return DocumentDetailResponse(
            id=doc.id,
            filename=doc.filename,
            title=doc.title,
            authors=doc.authors,
            created_at=doc.created_at,
            status=doc.status,
            page_count=doc.page_count,
            file_size=doc.file_size,
            chunk_count=len(chunks_resp),
            error_message=doc.error_message,
            pages=pages_resp,
            chunks=chunks_resp,
        )

    async def delete_document(self, document_id: str) -> dict[str, str]:
        """Deletes a document, its database records, and its physical file."""
        doc = await self.db.scalar(select(Document).where(Document.id == document_id))
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found.",
            )

        file_path = Path(doc.file_path)
        if file_path.exists():
            try:
                os.remove(file_path)
            except OSError as e:
                logger.warning("Failed to remove physical file %s: %s", file_path, str(e))

        await self.db.execute(delete(Document).where(Document.id == document_id))
        await self.db.commit()
        logger.info("Deleted document %s and its derived chunks/pages", document_id)

        return {"message": f"Document {document_id} successfully deleted."}
