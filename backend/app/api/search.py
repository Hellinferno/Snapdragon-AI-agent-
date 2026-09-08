from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.rag import SearchRequest, SearchResponse
from app.services.retrieval_service import RetrievalService

router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """
    Search indexed research documents.
    Returns ranked, source-aware chunks with document, page, and section metadata.
    """
    service = RetrievalService(db)
    return await service.search(
        query=request.query,
        top_k=request.top_k,
        document_ids=request.document_ids,
    )
