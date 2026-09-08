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

    async def save_image(self, file: UploadFile) -> ImageUploadResponse:
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

        return ImageUploadResponse(
            image_id=image_id,
            filename=clean_name,
            file_size=len(content),
            dimensions=dimensions,
            mime_type=mime_type,
            preview_url=f"/api/vision/{image_id}/file",
        )

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

    async def chat_with_figure(self, image_id: str, question: str) -> VisualQAResponse:
        path, filename = self._find_image_file(image_id)
        with open(path, "rb") as f:
            content = f.read()

        result = await self.vision_provider.answer_question(content, question, filename)
        return VisualQAResponse(
            image_id=image_id,
            question=question,
            answer=result.answer,
            grounded_visual_cues=result.grounded_visual_cues,
        )

    def get_image_path(self, image_id: str) -> Path:
        path, _ = self._find_image_file(image_id)
        return path

    async def save_raw_image(self, content: bytes, filename: str) -> ImageUploadResponse:
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

        return ImageUploadResponse(
            image_id=image_id,
            filename=clean_name,
            file_size=len(content),
            dimensions=dimensions,
            mime_type=mime_type,
            preview_url=f"/api/vision/{image_id}/file",
        )


vision_service = VisionService()

