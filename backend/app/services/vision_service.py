import io
import os
import re
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from PIL import Image

from app.core.config import settings
from app.core.logging import logger
from app.providers.base import VisionProvider
from app.providers.factory import get_vision_provider
from app.schemas.vision import (
    FigureAnalysisResponse,
    ImageUploadResponse,
    VisualQAResponse,
)
from app.services.retrieval_service import RetrievalService

# Number of chunks retrieved from the linked paper for paper-context Q&A
PAPER_CONTEXT_TOP_K = 3

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


def get_image_storage_dir() -> Path:
    img_dir = settings.DATA_DIR / "uploads" / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    return img_dir


class VisionService:
    def __init__(self, vision: VisionProvider | None = None):
        self.storage_dir = get_image_storage_dir()
        self.vision_provider = vision or get_vision_provider()

    async def save_image(
        self,
        file: UploadFile,
        document_id: str | None = None,
    ) -> ImageUploadResponse:
        filename = file.filename or "figure.png"
        clean_name = re.sub(r"[^\w\s\.-]", "_", Path(filename).name)
        ext = Path(clean_name).suffix.lower()

        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image format '{ext}'. Allowed: PNG, JPG, JPEG, WEBP.",
            )

        content = await file.read()
        if len(content) > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image exceeds 20MB limit.",
            )

        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded image file is empty.",
            )

        try:
            image = Image.open(io.BytesIO(content))
            dimensions = image.size
            mime_type = Image.MIME.get(image.format, f"image/{ext.lstrip('.')}")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or corrupted image: {str(e)}",
            )

        image_id = str(uuid.uuid4())
        saved_filename = f"{image_id}_{clean_name}"
        target_path = self.storage_dir / saved_filename

        with open(target_path, "wb") as f:
            f.write(content)

        logger.info("Saved research figure %s (%dx%d)", saved_filename, dimensions[0], dimensions[1])

        if document_id:
            self._write_document_link(image_id, document_id)

        return ImageUploadResponse(
            image_id=image_id,
            filename=clean_name,
            file_size=len(content),
            dimensions=dimensions,
            mime_type=mime_type,
            preview_url=f"/api/vision/{image_id}/file",
            document_id=document_id,
        )

    def _write_document_link(self, image_id: str, document_id: str) -> None:
        """Persist the figure-to-paper link as a sidecar file next to the image."""
        try:
            (self.storage_dir / f"{image_id}__link.txt").write_text(
                document_id, encoding="utf-8"
            )
        except OSError as e:
            logger.warning("Could not persist figure-document link for %s: %s", image_id, e)

    def _find_image_file(self, image_id: str) -> tuple[Path, str]:
        pattern = f"{image_id}_*"
        matches = list(self.storage_dir.glob(pattern))
        if not matches:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Figure with ID {image_id} not found.",
            )
        path = matches[0]
        original_filename = path.name[len(image_id) + 1:]
        return path, original_filename

    async def analyze_figure(self, image_id: str) -> FigureAnalysisResponse:
        path, filename = self._find_image_file(image_id)
        with open(path, "rb") as f:
            content = f.read()

        result = await self.vision_provider.analyze_figure(content, filename)
        return FigureAnalysisResponse(
            image_id=image_id,
            figure_type=result.figure_type,
            title=result.title,
            summary=result.summary,
            observations=result.observations,
            confidence=result.confidence,
        )

    async def chat_with_figure(
        self,
        image_id: str,
        question: str,
        document_id: str | None = None,
    ) -> VisualQAResponse:
        path, filename = self._find_image_file(image_id)
        with open(path, "rb") as f:
            content = f.read()

        result = await self.vision_provider.answer_question(content, question, filename)

        paper_sources = []
        paper_context_block = ""
        effective_doc_id = document_id or self._linked_document_id(image_id)
        if effective_doc_id:
            paper_sources, paper_context_block = await self._retrieve_paper_context(
                effective_doc_id, question
            )

        answer = result.answer
        if paper_context_block:
            answer = (
                f"{answer}\n\n**Paper Context** (from the linked document):\n{paper_context_block}"
            )

        return VisualQAResponse(
            image_id=image_id,
            question=question,
            answer=answer,
            grounded_visual_cues=result.grounded_visual_cues,
            paper_context_sources=paper_sources,
        )

    async def _retrieve_paper_context(
        self, document_id: str, question: str
    ) -> tuple[list, str]:
        """Retrieve cited chunks from the linked paper relevant to the question.

        Returns (sources, formatted block). Retrieval failures degrade gracefully:
        figure Q&A still works, just without paper context.
        """
        try:
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.core.database import get_db_session

            async for db in get_db_session():
                retrieval = RetrievalService(db)
                search_res = await retrieval.search(
                    query=question,
                    top_k=PAPER_CONTEXT_TOP_K,
                    document_ids=[document_id],
                    min_score=0.01,
                )
                if not search_res.results:
                    return [], ""
                lines = []
                for src in search_res.results:
                    sec = f", Section: {src.section}" if src.section else ""
                    lines.append(
                        f"- {src.excerpt} [Doc: {src.document_title}, Page: {src.page_number}{sec}]"
                    )
                return search_res.results, "\n".join(lines)
        except Exception as e:  # noqa: BLE001 - paper context is best-effort
            logger.warning("Paper-context retrieval failed for doc %s: %s", document_id, e)
        return [], ""

    def _linked_document_id(self, image_id: str) -> str | None:
        """Return the document id linked at upload time, if any (best-effort)."""
        link_file = self.storage_dir / f"{image_id}__link.txt"
        if link_file.exists():
            try:
                value = link_file.read_text(encoding="utf-8").strip()
                return value or None
            except OSError:
                return None
        return None

    def get_image_path(self, image_id: str) -> Path:
        path, _ = self._find_image_file(image_id)
        return path

    async def save_raw_image(
        self,
        content: bytes,
        filename: str,
        document_id: str | None = None,
    ) -> ImageUploadResponse:
        """Saves raw image bytes directly from disk or generator."""
        clean_name = re.sub(r"[^\w\s\.-]", "_", Path(filename).name)
        ext = Path(clean_name).suffix.lower() or ".png"

        image = Image.open(io.BytesIO(content))
        dimensions = image.size
        mime_type = Image.MIME.get(image.format, f"image/{ext.lstrip('.')}")

        image_id = str(uuid.uuid4())[:8]
        stored_filename = f"{image_id}_{clean_name}"
        stored_path = self.storage_dir / stored_filename

        with open(stored_path, "wb") as f:
            f.write(content)

        if document_id:
            self._write_document_link(image_id, document_id)

        return ImageUploadResponse(
            image_id=image_id,
            filename=clean_name,
            file_size=len(content),
            dimensions=dimensions,
            mime_type=mime_type,
            preview_url=f"/api/vision/{image_id}/file",
            document_id=document_id,
        )


vision_service = VisionService()

