"""Central Provider Factory resolving AI providers based on configuration."""

from typing import Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.providers.base import EmbeddingProvider, LLMProvider, VisionProvider, OCRProvider
from app.providers.embedding_provider import DevelopmentEmbeddingProvider
from app.providers.gemini_provider import GeminiLLMProvider
from app.providers.openrouter_provider import OpenRouterProvider
from app.providers.llm_provider import DevelopmentLLMProvider
from app.providers.vision_provider import DevelopmentVisionProvider, DevelopmentOCRProvider
from app.providers.qualcomm.qualcomm_config import QualcommConfig
from app.providers.qualcomm.qualcomm_providers import (
    QualcommEmbeddingProvider,
    QualcommLLMProvider,
    QualcommVisionProvider,
)

logger = get_logger(__name__)


def get_embedding_provider(backend: Optional[str] = None) -> EmbeddingProvider:
    """Return the configured EmbeddingProvider."""
    effective_backend = (backend or settings.EMBEDDING_PROVIDER or settings.PROVIDER_BACKEND).lower()
    if effective_backend == "qualcomm":
        logger.info("Instantiating QualcommEmbeddingProvider (Snapdragon target).")
        cfg = QualcommConfig(
            device_target=settings.QUALCOMM_DEVICE_TARGET,
            model_dir=settings.QUALCOMM_MODEL_DIR,
            qnn_backend_path=settings.QUALCOMM_BACKEND_PATH,
            htp_performance_mode=settings.QUALCOMM_PERFORMANCE_MODE,
        )
        return QualcommEmbeddingProvider(cfg)
    if effective_backend == "onnx_minilm":
        from app.providers.onnx_embedding_provider import OnnxMiniLMEmbeddingProvider

        return OnnxMiniLMEmbeddingProvider(settings.EMBEDDING_MODEL_DIR)
    return DevelopmentEmbeddingProvider()


def get_llm_provider(backend: Optional[str] = None) -> LLMProvider:
    """Return the configured LLMProvider."""
    effective_backend = (backend or settings.LLM_PROVIDER or settings.PROVIDER_BACKEND).lower()
    if effective_backend in ("openrouter", "openrouter_api"):
        if not settings.ALLOW_EXTERNAL_PROVIDERS:
            raise ValueError(
                "External cloud providers are disabled by default to guarantee local privacy. "
                "Set ALLOW_EXTERNAL_PROVIDERS=true in your environment to explicitly opt-in."
            )
        return OpenRouterProvider()
    if effective_backend == "gemini":
        if not settings.ALLOW_EXTERNAL_PROVIDERS:
            raise ValueError(
                "External cloud providers are disabled by default to guarantee local privacy. "
                "Set ALLOW_EXTERNAL_PROVIDERS=true in your environment to explicitly opt-in."
            )
        return GeminiLLMProvider()

    if effective_backend == "qualcomm":
        logger.info("Instantiating QualcommLLMProvider (Snapdragon target).")
        cfg = QualcommConfig(
            device_target=settings.QUALCOMM_DEVICE_TARGET,
            model_dir=settings.QUALCOMM_MODEL_DIR,
            qnn_backend_path=settings.QUALCOMM_BACKEND_PATH,
            htp_performance_mode=settings.QUALCOMM_PERFORMANCE_MODE,
        )
        return QualcommLLMProvider(cfg)
    return DevelopmentLLMProvider()


def get_vision_provider(backend: Optional[str] = None) -> VisionProvider:
    """Return the configured VisionProvider."""
    effective_backend = (backend or settings.VISION_PROVIDER or settings.PROVIDER_BACKEND).lower()
    if effective_backend == "qualcomm":
        logger.info("Instantiating QualcommVisionProvider (Snapdragon target).")
        cfg = QualcommConfig(
            device_target=settings.QUALCOMM_DEVICE_TARGET,
            model_dir=settings.QUALCOMM_MODEL_DIR,
            qnn_backend_path=settings.QUALCOMM_BACKEND_PATH,
            htp_performance_mode=settings.QUALCOMM_PERFORMANCE_MODE,
        )
        return QualcommVisionProvider(cfg)
    return DevelopmentVisionProvider()


def get_ocr_provider(backend: Optional[str] = None) -> OCRProvider:
    """Return the configured OCRProvider."""
    return DevelopmentOCRProvider()
