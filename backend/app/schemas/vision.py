from pydantic import BaseModel, Field


class ImageUploadResponse(BaseModel):
    image_id: str
    filename: str
    file_size: int
    dimensions: tuple[int, int]
    mime_type: str
    preview_url: str


class FigureAnalysisRequest(BaseModel):
    image_id: str


class FigureAnalysisResponse(BaseModel):
    image_id: str
    figure_type: str
    title: str
    summary: str
    observations: list[str]
    confidence: float


class VisualQARequest(BaseModel):
    image_id: str
    question: str = Field(..., min_length=1, description="Question regarding the research figure or diagram")


class VisualQAResponse(BaseModel):
    image_id: str
    question: str
    answer: str
    grounded_visual_cues: list[str]
