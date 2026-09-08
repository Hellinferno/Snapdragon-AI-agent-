from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint confirming service and AI provider runtime status."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "provider_backend": settings.PROVIDER_BACKEND,
        "llm_provider": settings.LLM_PROVIDER or settings.PROVIDER_BACKEND,
        "embedding_provider": settings.EMBEDDING_PROVIDER or settings.PROVIDER_BACKEND,
        "vision_provider": settings.VISION_PROVIDER or settings.PROVIDER_BACKEND,
        "external_providers_enabled": settings.ALLOW_EXTERNAL_PROVIDERS,
        "device_target": settings.QUALCOMM_DEVICE_TARGET,
    }
