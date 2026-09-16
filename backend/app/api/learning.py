from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.learning import (
    ExplainRequest,
    ExplainResponse,
    FlashcardsRequest,
    FlashcardsResponse,
    QuizRequest,
    QuizResponse,
)
from app.services.learning_service import LearningService

router = APIRouter()


@router.post("/explain", response_model=ExplainResponse)
async def explain_concept(
    request: ExplainRequest,
    db: AsyncSession = Depends(get_db),
) -> ExplainResponse:
    """
    Explains an academic concept at a specified depth (beginner, intermediate, deep_dive).
    Returns synthesized pedagogical explanation with key takeaways and citations.
    """
    service = LearningService(db)
    return await service.explain_concept(
        concept=request.concept,
        document_ids=request.document_ids,
        level=request.level,
    )


@router.post("/quiz", response_model=QuizResponse)
async def generate_quiz(
    request: QuizRequest,
    db: AsyncSession = Depends(get_db),
) -> QuizResponse:
    """
    Generates a structured multiple-choice quiz grounded in indexed documents.
    Every question includes options, the correct answer index, and verified citation evidence.
    """
    service = LearningService(db)
    return await service.generate_quiz(
        document_ids=request.document_ids,
        question_count=request.question_count,
        difficulty=request.difficulty,
    )


@router.post("/flashcards", response_model=FlashcardsResponse)
async def generate_flashcards(
    request: FlashcardsRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> FlashcardsResponse:
    """Generates active-recall study flashcards from indexed material."""
    doc_ids = request.document_ids if request else None
    service = LearningService(db)
    return await service.generate_flashcards(document_ids=doc_ids)
