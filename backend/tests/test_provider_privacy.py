import pytest

from app.providers.factory import get_llm_provider
from app.providers.gemini_provider import GeminiLLMProvider
from app.providers.llm_provider import DevelopmentLLMProvider
from app.providers.qualcomm.qualcomm_providers import QualcommEmbeddingProvider, QualcommLLMProvider
from app.services.retrieval_service import RetrievalService
from app.core.config import settings


@pytest.mark.asyncio
async def test_development_llm_never_uses_an_environment_api_key(monkeypatch: pytest.MonkeyPatch):
    """An ambient credential must not turn the local provider into a cloud provider."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    result = await DevelopmentLLMProvider().generate(
        "### CONTEXT:\nNO_RELEVANT_EVIDENCE\n### QUESTION:\nWhat is in this document?"
    )

    assert "Insufficient evidence" in result.text


def test_factory_selects_gemini_only_when_explicitly_requested(monkeypatch: pytest.MonkeyPatch):
    """The application may use Gemini only through an explicit provider selection and opt-in."""
    monkeypatch.setattr(settings, "ALLOW_EXTERNAL_PROVIDERS", False)
    with pytest.raises(ValueError, match="External cloud providers are disabled by default"):
        get_llm_provider("gemini")

    monkeypatch.setattr(settings, "ALLOW_EXTERNAL_PROVIDERS", True)
    assert isinstance(get_llm_provider("gemini"), GeminiLLMProvider)


def test_retrieval_service_uses_the_configured_provider_backend(monkeypatch: pytest.MonkeyPatch):
    """Changing the configured backend must change the providers handling requests."""
    monkeypatch.setattr(settings, "PROVIDER_BACKEND", "qualcomm")
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", None)
    monkeypatch.setattr(settings, "LLM_PROVIDER", None)

    service = RetrievalService(object())

    assert isinstance(service.embedding_provider, QualcommEmbeddingProvider)
    assert isinstance(service.llm_provider, QualcommLLMProvider)
