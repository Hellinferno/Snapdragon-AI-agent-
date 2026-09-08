from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.research import CompareRequest, CompareResponse
from app.services.comparison_service import ComparisonService

router = APIRouter()


@router.post("/compare", response_model=CompareResponse)
async def compare_documents(
    request: CompareRequest,
    db: AsyncSession = Depends(get_db),
) -> CompareResponse:
    """
    Compares two or more research documents across selected dimensions.
    Returns side-by-side dimension breakdowns, cross-paper synthesis, and citations.
    """
    service = ComparisonService(db)
    return await service.compare_documents(
        document_ids=request.document_ids,
        dimensions=request.dimensions,
    )
