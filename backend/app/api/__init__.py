from fastapi import APIRouter
from app.api.chat import router as chat_router
from app.api.demo import router as demo_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.learning import router as learning_router
from app.api.research import router as research_router
from app.api.search import router as search_router
from app.api.vision import router as vision_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(demo_router, tags=["Demo"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(search_router, prefix="/search", tags=["Search"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(research_router, prefix="/research", tags=["Research"])
api_router.include_router(learning_router, prefix="/learning", tags=["Learning"])
api_router.include_router(vision_router, prefix="/vision", tags=["Vision"])

__all__ = ["api_router"]

