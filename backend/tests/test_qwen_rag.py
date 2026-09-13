"""
Integration tests for Qwen through OpenRouter as the RAG LLM backend.
Verifies: model selection, payload structure, grounding prompt inclusion,
response parsing, token usage capture, and error handling.
"""
import pytest
import httpx
from httpx import Response
from app.core.config import settings
from app.providers.factory import get_llm_provider
from app.providers.openrouter_provider import OpenRouterProvider
from app.services.context_builder import (
    GROUNDING_SYSTEM_PROMPT,
    build_context_block,
    build_rag_prompt,
)
from app.schemas.rag import SourceReference


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

QWEN_MODEL = "qwen/qwen-2.5-72b-instruct"

SAMPLE_SOURCE = SourceReference(
    document_id="doc-001",
    document_title="Multimodal Transformers for Diagnostic Radiology",
    page_number=4,
    chunk_id="chunk-001",
    relevance_score=0.92,
    section="Results",
    excerpt="The multimodal model achieved an AUC of 91.4% for pneumonia detection across 5,000 chest X-rays.",
)


def _make_mock_response(content: str, model: str = QWEN_MODEL) -> dict:
    return {
        "id": "test-id",
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 150, "completion_tokens": 42},
    }


# ---------------------------------------------------------------------------
# Test 1 — Factory correctly selects OpenRouter with Qwen
# ---------------------------------------------------------------------------

def test_factory_selects_openrouter_with_qwen(monkeypatch: pytest.MonkeyPatch):
    """factory.get_llm_provider('openrouter') must return OpenRouterProvider."""
    monkeypatch.setattr(settings, "ALLOW_EXTERNAL_PROVIDERS", True)
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", QWEN_MODEL)

    provider = get_llm_provider("openrouter")

    assert isinstance(provider, OpenRouterProvider)
    assert QWEN_MODEL in provider.name


# ---------------------------------------------------------------------------
# Test 2 — Provider sends Qwen model ID, system prompt, and context in payload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_openrouter_sends_qwen_model_and_grounding_prompt(monkeypatch: pytest.MonkeyPatch):
    """Verify the correct Qwen model ID and system prompt are sent to OpenRouter."""
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", QWEN_MODEL)
    monkeypatch.setattr(settings, "OPENROUTER_MAX_TOKENS", 1024)

    captured = {}

    async def mock_post(self, url, *args, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json", {})
        req = httpx.Request("POST", url)
        return Response(200, json=_make_mock_response("Answer grounded in context."), request=req)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    provider = OpenRouterProvider()
    context_block = build_context_block([SAMPLE_SOURCE])
    prompt = build_rag_prompt(
        "What AUC did the model achieve for pneumonia?",
        context_block,
    )
    result = await provider.generate(prompt, system_prompt=GROUNDING_SYSTEM_PROMPT)

    payload = captured["json"]
    messages = payload["messages"]

    # Qwen model sent
    assert payload["model"] == QWEN_MODEL, f"Expected {QWEN_MODEL}, got {payload['model']}"

    # max_tokens respected
    assert payload["max_tokens"] == 1024

    # System prompt (grounding rules) is first message
    assert messages[0]["role"] == "system"
    assert "Insufficient evidence" in messages[0]["content"]
    assert "CONTEXT" in messages[0]["content"]

    # User message contains the RAG prompt with context
    user_msg = messages[1]["content"]
    assert "### CONTEXT:" in user_msg
    assert "AUC" in user_msg
    assert "### QUESTION:" in user_msg

    # Response parsed correctly
    assert result.text == "Answer grounded in context."
    assert result.prompt_tokens == 150
    assert result.completion_tokens == 42


# ---------------------------------------------------------------------------
# Test 3 — Provider refuses when OPENROUTER_API_KEY is missing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_openrouter_raises_when_key_missing(monkeypatch: pytest.MonkeyPatch):
    """Provider must raise RuntimeError when no API key is configured."""
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", None)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    provider = OpenRouterProvider()
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY is not configured"):
        await provider.generate("Any question")


# ---------------------------------------------------------------------------
# Test 4 — Context builder produces valid source block format
# ---------------------------------------------------------------------------

def test_context_builder_produces_source_citations():
    """build_context_block must produce [Source N: "Title", Page X] headers."""
    block = build_context_block([SAMPLE_SOURCE])

    assert '[Source 1: "Multimodal Transformers for Diagnostic Radiology", Page 4' in block
    assert "91.4%" in block
    assert "Results" in block  # section included


def test_context_builder_returns_no_evidence_sentinel_when_empty():
    """build_context_block must return NO_RELEVANT_EVIDENCE when no sources."""
    block = build_context_block([])
    assert block == "NO_RELEVANT_EVIDENCE"


# ---------------------------------------------------------------------------
# Test 5 — Grounding prompt contains all required rules
# ---------------------------------------------------------------------------

def test_grounding_system_prompt_contains_required_rules():
    """System prompt must contain the 7 critical grounding rules."""
    prompt = GROUNDING_SYSTEM_PROMPT
    assert "ONLY" in prompt                          # rule 1: context only
    assert "[Doc:" in prompt                          # rule 2: citation format
    assert "Insufficient evidence" in prompt          # rule 3: refusal phrase
    assert "training data" in prompt                  # rule 4: no external knowledge
    assert "cite all of them" in prompt               # rule 5: multi-source citation
    assert "state the finding" in prompt              # rule 7: answer structure
