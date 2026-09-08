from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import FileResponse

from app.schemas.vision import (
    FigureAnalysisRequest,
    FigureAnalysisResponse,
    ImageUploadResponse,
    VisualQARequest,
    VisualQAResponse,
)
from app.services.vision_service import VisionService

router = APIRouter()
vision_service = VisionService()


@router.post("/upload", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_figure(file: UploadFile = File(...)) -> ImageUploadResponse:
    """Uploads a research figure or screenshot for visual understanding."""
    return await vision_service.save_image(file)


@router.post("/analyze", response_model=FigureAnalysisResponse)
async def analyze_figure(request: FigureAnalysisRequest) -> FigureAnalysisResponse:
    """Decomposes a figure into structural observations, metrics, and type classification."""
    return await vision_service.analyze_figure(request.image_id)


@router.post("/chat", response_model=VisualQAResponse)
async def chat_with_figure(request: VisualQARequest) -> VisualQAResponse:
    """Grounded question answering focused on the visual evidence in the figure."""
    return await vision_service.chat_with_figure(request.image_id, request.question)


@router.get("/{image_id}/file")
async def get_figure_file(image_id: str):
    """Serves the physical image file for visual display."""
    path = vision_service.get_image_path(image_id)
    return FileResponse(str(path))
