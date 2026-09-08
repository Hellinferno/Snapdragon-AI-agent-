from fastapi import APIRouter
from app.api.documents import router as documents_router
from app.api.health import router as health_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])

__all__ = ["api_router"]
