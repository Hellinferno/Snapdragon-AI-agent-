"""Tests for the LLM-backed Learning Studio with template fallback.

Verifies:
- With a generative LLM (mocked), explain/quiz/flashcards use LLM output when it
  is valid and properly cited.
- Invalid JSON, missing citations, or provider failures fall back to the
  deterministic template path.
- The development provider (non-generative) always takes the template path.
"""

import json
from unittest.mock import AsyncMock

import pytest

from app.providers.base import GenerationResult, LLMProvider
from app.services.learning_service import LearningService


class _FakeRetrieval:
    """Returns the given sources from every search call."""

    def __init__(self, sources):
        self._sources = sources

    async def search(self, **_):
        from app.schemas.rag import SearchResponse

        return SearchResponse(query="x", results=list(self._sources))


def _make_source(title: str = "Quantization Study", page: int = 2) -> "SourceReference":
    from app.schemas.rag import SourceReference

    return SourceReference(
        document_id="doc-1",
        document_title=title,
        page_number=page,
        chunk_id="chunk-1",
        relevance_score=0.9,
        section="Results",
        excerpt="INT4 weights reduced model size in the evaluated experiment.",
    )


class _GenerativeFakeLLM(LLMProvider):
    """Stands in for OpenRouter/Gemini: name contains no 'development'."""

    def __init__(self, text: str):
        self._text = text
        self.calls: list[tuple[str, str | None]] = []

    @property
    def name(self) -> str:
        return "fake-generative-llm"

    async def generate(self, prompt: str, system_prompt: str | None = None):
        self.calls.append((prompt, system_prompt))
        return GenerationResult(text=self._text, prompt_tokens=10, completion_tokens=10)


class _FailingLLM(LLMProvider):
    @property
    def name(self) -> str:
        return "fake-failing-llm"

    async def generate(self, prompt: str, system_prompt: str | None = None):
        raise RuntimeError("provider down")


# ---------------------------------------------------------------------------
# Gate: development provider must take the template path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_development_provider_uses_template_path():
    service = LearningService(None)
    assert service._llm_is_generative() is False


@pytest.mark.asyncio
async def test_generative_provider_detected():
    service = LearningService(None, llm=_GenerativeFakeLLM("x"))
    assert service._llm_is_generative() is True


# ---------------------------------------------------------------------------
# Explain: LLM path and fallbacks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explain_uses_llm_when_cited():
    llm = _GenerativeFakeLLM(
        "INT4 quantization shrinks model memory with minimal accuracy loss "
        "[Doc: Quantization Study, Page: 2].\n\nKEY TAKEAWAYS:\n"
        "- INT4 reduces size [Doc: Quantization Study, Page: 2]\n"
        "- Accuracy held in the evaluated experiment"
    )
    src = _make_source()
    service = LearningService(None, llm=llm)
    service.retrieval_service = _FakeRetrieval([src])

    res = await service.explain_concept("quantization", level="intermediate")

    assert "[Doc: Quantization Study, Page: 2]" in res.explanation
    assert len(res.key_takeaways) == 2
    assert res.sources[0].chunk_id == "chunk-1"
    # Pedagogy system prompt was sent
    assert llm.calls[0][1] is not None and "tutor" in llm.calls[0][1]


@pytest.mark.asyncio
async def test_explain_falls_back_when_llm_omits_citations():
    llm = _GenerativeFakeLLM("A plausible-sounding explanation with no citations at all.")
    src = _make_source()
    service = LearningService(None, llm=llm)
    service.retrieval_service = _FakeRetrieval([src])

    res = await service.explain_concept("quantization", level="beginner")

    # Template output is grounded and carries the source label
    assert "INT4 weights reduced model size" in res.explanation
    assert "[Doc: Quantization Study, Page: 2]" in res.explanation


@pytest.mark.asyncio
async def test_explain_falls_back_when_llm_raises():
    src = _make_source()
    service = LearningService(None, llm=_FailingLLM())
    service.retrieval_service = _FakeRetrieval([src])

    res = await service.explain_concept("quantization")

    assert "INT4 weights reduced model size" in res.explanation


# ---------------------------------------------------------------------------
# Quiz: LLM JSON path and fallbacks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quiz_uses_valid_llm_json():
    src = _make_source()
    payload = [
        {
            "question": "What effect did INT4 weights have in the evaluated experiment?",
            "options": [
                "They reduced model size.",
                "They tripled latency.",
                "They degraded accuracy below baseline.",
                "They had no measurable effect.",
            ],
            "correct_index": 0,
            "explanation": "The study reports size reduction [Doc: Quantization Study, Page: 2].",
        }
    ]
    llm = _GenerativeFakeLLM(json.dumps(payload))
    service = LearningService(None, llm=llm)
    service.retrieval_service = _FakeRetrieval([src])

    res = await service.generate_quiz(question_count=1, difficulty="medium")

    assert len(res.questions) == 1
    q = res.questions[0]
    assert q.correct_answer_index == 0
    assert q.correct_answer == "They reduced model size."
    assert "Quantization Study" in q.explanation
    assert q.source.chunk_id == "chunk-1"


@pytest.mark.asyncio
async def test_quiz_falls_back_on_invalid_json():
    src = _make_source()
    llm = _GenerativeFakeLLM("This is not JSON at all.")
    service = LearningService(None, llm=llm)
    service.retrieval_service = _FakeRetrieval([src])

    res = await service.generate_quiz(question_count=1)

    # Template quiz question text pattern
    assert res.questions[0].question.startswith("According to")
    assert res.questions[0].source is not None


@pytest.mark.asyncio
async def test_quiz_rejects_uncited_llm_questions():
    src = _make_source()
    payload = [
        {
            "question": "What effect did INT4 weights have?",
            "options": ["A", "B", "C", "D"],
            "correct_index": 0,
            "explanation": "No citation included here.",
        }
    ]
    llm = _GenerativeFakeLLM(json.dumps(payload))
    service = LearningService(None, llm=llm)
    service.retrieval_service = _FakeRetrieval([src])

    res = await service.generate_quiz(question_count=1)

    # Uncited LLM question rejected -> template fallback
    assert res.questions[0].question.startswith("According to")


@pytest.mark.asyncio
async def test_quiz_json_in_markdown_fence_is_parsed():
    src = _make_source()
    payload = json.dumps(
        [
            {
                "question": "What did INT4 weights reduce?",
                "options": ["size", "latency", "cost", "energy"],
                "correct_index": 0,
                "explanation": "Per the study [Doc: Quantization Study, Page: 2].",
            }
        ]
    )
    llm = _GenerativeFakeLLM(f"```json\n{payload}\n```")
    service = LearningService(None, llm=llm)
    service.retrieval_service = _FakeRetrieval([src])

    res = await service.generate_quiz(question_count=1)

    assert res.questions[0].correct_answer == "size"


# ---------------------------------------------------------------------------
# Flashcards: LLM path and fallbacks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flashcards_use_valid_llm_json():
    src = _make_source()
    payload = [
        {
            "front": "What did INT4 weights reduce in the evaluated experiment?",
            "back": "Model size [Doc: Quantization Study, Page: 2].",
        }
    ]
    llm = _GenerativeFakeLLM(json.dumps(payload))
    service = LearningService(None, llm=llm)
    service.retrieval_service = _FakeRetrieval([src])

    res = await service.generate_flashcards(count=1)

    assert len(res.flashcards) == 1
    assert "Model size" in res.flashcards[0].back_answer
    assert "Quantization Study" in res.flashcards[0].source_hint


@pytest.mark.asyncio
async def test_flashcards_fall_back_on_provider_failure():
    src = _make_source()
    service = LearningService(None, llm=_FailingLLM())
    service.retrieval_service = _FakeRetrieval([src])

    res = await service.generate_flashcards(count=1)

    assert len(res.flashcards) == 1
    assert "INT4 weights reduced model size" in res.flashcards[0].back_answer


# ---------------------------------------------------------------------------
# Grounding filter: weak chunks never reach the LLM
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_weak_sources_skip_llm_and_use_templates():
    src = _make_source()
    src.relevance_score = 0.02  # below MIN_GROUNDING_SCORE
    llm = _GenerativeFakeLLM(json.dumps([]))
    service = LearningService(None, llm=llm)
    service.retrieval_service = _FakeRetrieval([src])

    res = await service.generate_flashcards(count=1)

    assert llm.calls == []  # LLM never invoked
    assert len(res.flashcards) == 1
