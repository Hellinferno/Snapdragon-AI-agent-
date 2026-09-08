import pytest

from app.schemas.rag import SearchResponse, SourceReference
from app.schemas.research import DocumentComparisonItem
from app.services.comparison_service import ComparisonService
from app.services.learning_service import LearningService


def test_comparison_synthesis_does_not_invent_cross_paper_claims():
    """No evidence must produce an explicit evidence gap, not a stock narrative."""
    comparisons = [
        DocumentComparisonItem(
            document_id="a",
            document_title="Paper A",
            dimension_values={"Methodology": "No explicit details found for Methodology in indexed sections."},
        ),
        DocumentComparisonItem(
            document_id="b",
            document_title="Paper B",
            dimension_values={"Methodology": "No explicit details found for Methodology in indexed sections."},
        ),
    ]

    synthesis = ComparisonService(None)._build_synthesis(comparisons, ["Methodology"])

    assert "No source-backed comparison evidence was retrieved" in synthesis
    assert "direct execution/algorithmic design" not in synthesis


class _SingleSourceRetrieval:
    async def search(self, **_: object) -> SearchResponse:
        return SearchResponse(
            query="quantization",
            results=[
                SourceReference(
                    document_id="doc-1",
                    document_title="Quantization Study",
                    page_number=2,
                    chunk_id="chunk-1",
                    relevance_score=0.9,
                    excerpt="INT4 weights reduced model size in the evaluated experiment.",
                )
            ],
        )


@pytest.mark.asyncio
async def test_learning_explanation_contains_only_retrieved_evidence():
    """A sourced explanation must not add unverified privacy or latency guarantees."""
    service = LearningService(None)
    service.retrieval_service = _SingleSourceRetrieval()

    response = await service.explain_concept("quantization", level="beginner")

    assert "INT4 weights reduced model size" in response.explanation
    assert "without sending your private work" not in response.explanation
    assert "guarantees deterministic inference latencies" not in response.explanation
