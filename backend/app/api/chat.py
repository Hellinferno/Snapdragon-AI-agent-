from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.rag import ChatRequest, ChatResponse
from app.services.retrieval_service import RetrievalService

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat_with_documents(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Grounded question-answering across indexed research documents.
    Synthesizes answers backed by source citations and flags insufficient evidence.
    """
    service = RetrievalService(db)
    return await service.chat(
        question=request.question,
        top_k=request.top_k,
        document_ids=request.document_ids,
    )
