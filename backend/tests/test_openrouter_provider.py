import pytest
from httpx import Response
from app.core.config import settings
from app.providers.factory import get_llm_provider
from app.providers.openrouter_provider import OpenRouterProvider


def test_factory_selects_openrouter_only_when_explicitly_requested(monkeypatch: pytest.MonkeyPatch):
    """Factory must refuse to instantiate OpenRouter unless ALLOW_EXTERNAL_PROVIDERS=true."""
    monkeypatch.setattr(settings, "ALLOW_EXTERNAL_PROVIDERS", False)
    with pytest.raises(ValueError, match="External cloud providers are disabled by default"):
        get_llm_provider("openrouter")

    monkeypatch.setattr(settings, "ALLOW_EXTERNAL_PROVIDERS", True)
    provider = get_llm_provider("openrouter")
    assert isinstance(provider, OpenRouterProvider)
    assert provider.name.startswith("openrouter-")


@pytest.mark.asyncio
async def test_openrouter_provider_generate(monkeypatch: pytest.MonkeyPatch):
    """Test generation payload and response extraction via mocked httpx client."""
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key-123")
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", "google/gemini-2.5-flash")

    mock_response_json = {
        "choices": [
            {
                "message": {
                    "content": "This is a test answer from OpenRouter."
                }
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 8
        }
    }

    async def mock_post(self, url, *args, **kwargs):
        assert url == "https://openrouter.ai/api/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer test-key-123"
        assert kwargs["json"]["model"] == "google/gemini-2.5-flash"
        req = httpx.Request("POST", url)
        return Response(200, json=mock_response_json, request=req)



    provider = OpenRouterProvider()
    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    result = await provider.generate("What is the dataset name?", system_prompt="Answer concisely.")
    assert result.text == "This is a test answer from OpenRouter."
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 8
