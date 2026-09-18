"""Opt-in live-provider integration tests.

These tests verify REAL external connectivity (OpenRouter) and are intentionally
excluded from the standard automated suite, which must stay fully hermetic.

Run manually with real credentials:

    RUN_LIVE_TESTS=1 OPENROUTER_API_KEY=sk-... pytest -m live

Standard `pytest` runs skip everything in this module, so CI never requires an
external API.
"""

import os

import pytest

from app.core.config import settings

RUN_LIVE_TESTS = os.getenv("RUN_LIVE_TESTS", "").strip().lower() in ("1", "true", "yes")
HAS_API_KEY = bool(
    getattr(settings, "OPENROUTER_API_KEY", None)
    and str(settings.OPENROUTER_API_KEY).strip()
)

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not RUN_LIVE_TESTS,
        reason="Live integration tests are opt-in: set RUN_LIVE_TESTS=1 to enable.",
    ),
    pytest.mark.skipif(
        not HAS_API_KEY,
        reason="OPENROUTER_API_KEY is not configured.",
    ),
]


@pytest.mark.asyncio
async def test_openrouter_live_connectivity(monkeypatch: pytest.MonkeyPatch):
    """Real round-trip to OpenRouter: the provider must return a non-empty answer."""
    from app.providers.openrouter_provider import OpenRouterProvider

    monkeypatch.setattr(settings, "ALLOW_EXTERNAL_PROVIDERS", True)

    provider = OpenRouterProvider()
    result = await provider.generate(
        "Reply with the single word: connected",
        system_prompt="You are a connectivity probe. Answer with one word only.",
    )

    assert isinstance(result.text, str)
    assert len(result.text.strip()) > 0
    assert result.completion_tokens > 0


@pytest.mark.asyncio
async def test_openrouter_live_rag_round_trip(monkeypatch: pytest.MonkeyPatch):
    """End-to-end grounded answer through the real model with a tiny in-prompt context."""
    from app.services.context_builder import build_context_block, build_rag_prompt
    from app.schemas.rag import SourceReference
    from app.providers.openrouter_provider import OpenRouterProvider

    monkeypatch.setattr(settings, "ALLOW_EXTERNAL_PROVIDERS", True)

    source = SourceReference(
        document_id="live-doc-1",
        document_title="Live Connectivity Paper",
        page_number=1,
        chunk_id="live-chunk-1",
        relevance_score=0.99,
        section="Results",
        excerpt="The probe experiment reported a throughput of 42.0 requests per second.",
    )
    prompt = build_rag_prompt(
        "What throughput did the probe experiment report?",
        build_context_block([source]),
    )

    provider = OpenRouterProvider()
    result = await provider.generate(
        prompt,
        system_prompt=(
            "Answer using ONLY the context. Cite as [Doc: <title>, Page: <N>]. "
            "If the context lacks the answer, reply exactly: "
            "\"Insufficient evidence in the indexed documents to answer this question.\""
        ),
    )

    assert "42.0" in result.text
    assert "Live Connectivity Paper" in result.text
