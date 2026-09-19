"""Retrieval rank-quality regression guard for the demo corpus.

A future embedding, chunking, or fusion change must not silently degrade *ranking*
quality. Hit@k saturates on a corpus this small (doc hit is 100% even with the
feature-hash fallback), so only MRR and page recall@k can actually move — those are
what these floors protect.

The test indexes the three committed synthetic demo papers through the real pipeline
and scores them with the evaluation harness's own metrics, so it measures exactly what
`python -m evaluation.run_eval --dataset demo_papers --mode retrieval` reports.

Deterministic and offline: retrieval only (no LLM call is ever made), and the corpus
PDFs are sha256-verified against evaluation/datasets/demo_papers.json. The reference
values are the committed runs in evaluation/results/demo_papers/.

Floors are (reference - tolerance), with the tolerance sized to trip on a single
regression while absorbing float-level jitter:

    MRR             13 judged questions. One question falling from rank 1 to rank 2
                    costs 0.5 / 13 = 0.0385 of mean MRR, so tolerance 0.03.
    page recall@5   Per-question recall averaged over the same 13 questions. Losing
                    one of two expected pages costs 0.5 / 13 = 0.0385, so tolerance 0.03.

Raising a floor requires a new committed result file; lowering one silently would
defeat the purpose of this module.

What this guard can and cannot see on the demo corpus (measured, not assumed):

  * Covered: embedding-provider changes. Scoring the MiniLM case with the hash
    fallback yields MRR 0.7179, below the MiniLM floor, so an accidental provider
    downgrade fails loudly.
  * Covered: fusion changes and any change to chunk *text* (tokenization, hyphen
    repair, sentence splitting), since both move ranking.
  * Not visible here: CHUNK_SIZE_CHARS / CHUNK_OVERLAP_CHARS. Every demo page fits
    in a single chunk (5 pages -> 5 chunks per paper), so 600 vs 1200 chars measures
    identically. Chunk-size regressions need the larger book corpus, whose PDF is
    not redistributed; reproduce those with the run_eval commands in
    evaluation/README.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.providers.factory import get_embedding_provider
from app.providers.llm_provider import DevelopmentLLMProvider
from app.services.retrieval_service import RetrievalService
from evaluation.metrics import RetrievalSummary, judge_retrieval
from evaluation.run_eval import build_index, load_dataset, resolve_corpus, source_dict

DATASET = "demo_papers"
TOP_K = 5
# Measure ranking without the abstention threshold: retrieval quality is scored
# independently of whether chat() would have decided it had enough evidence.
MIN_SCORE = float("-inf")
TOLERANCE = 0.03

MODEL_READY = all(
    (settings.EMBEDDING_MODEL_DIR / name).exists() for name in ("model.onnx", "tokenizer.json")
)


@dataclass(frozen=True)
class RetrievalCase:
    label: str
    embedding_provider: str
    hybrid: bool
    reference_mrr: float
    reference_page_recall: float
    reference_source: str


CASES = [
    # The fallback path: what runs on a machine without the downloaded MiniLM model
    # (and what the test suite itself resolves, via conftest).
    RetrievalCase(
        label="hash-hybrid-fallback",
        embedding_provider="development",
        hybrid=True,
        reference_mrr=0.8718,
        reference_page_recall=0.75,
        reference_source="evaluation/results/demo_papers/p1_hybrid.json",
    ),
    # The recommended / default semantic path.
    RetrievalCase(
        label="minilm-vector-only",
        embedding_provider="onnx_minilm",
        hybrid=False,
        reference_mrr=0.8205,
        reference_page_recall=0.9231,
        reference_source="evaluation/results/demo_papers/p1b_minilm.json",
    ),
]


async def measure_retrieval(tmp_path, case: RetrievalCase, monkeypatch) -> RetrievalSummary:
    """Indexes the demo corpus in an isolated database and scores retrieval for it."""
    dataset, _ = load_dataset(DATASET)
    corpus = resolve_corpus(dataset, None)  # verifies each PDF's sha256 before indexing

    uploads = tmp_path / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(settings, "HYBRID_RETRIEVAL", case.hybrid)

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'retrieval_regression.db'}",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    embedding = get_embedding_provider(case.embedding_provider)
    summary = RetrievalSummary()
    try:
        async with session_factory() as session:
            await build_index(session, corpus, embedding)
            # An explicit development LLM keeps this test offline and independent of
            # how conftest resolves the provider; search() never calls it anyway.
            service = RetrievalService(session, embedding, DevelopmentLLMProvider())

            for question in dataset["questions"]:
                if not question["answerable"]:
                    continue
                search = await service.search(question["question"], top_k=TOP_K, min_score=MIN_SCORE)
                summary.add(judge_retrieval(question, [source_dict(s) for s in search.results]))
    finally:
        await engine.dispose()
    return summary


def _num(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def _report(summary: RetrievalSummary, case: RetrievalCase) -> str:
    return (
        f"\ncase={case.label} embedding={case.embedding_provider} hybrid={case.hybrid}\n"
        f"  reference ({case.reference_source}): mrr={case.reference_mrr:.4f} "
        f"page_recall@5={case.reference_page_recall:.4f}\n"
        f"  measured:  mrr={_num(summary.mrr.value)} page_recall@5={_num(summary.page_recall.value)} "
        f"evidence_hit@5={_num(summary.evidence_hit.value)} page_hit@5={_num(summary.page_hit.value)} "
        f"doc_hit@5={_num(summary.doc_hit.value)} (n={summary.mrr.count})\n"
        f"Floors exist so embedding/chunking changes cannot silently degrade rank quality. "
        f"If this drop is intentional, add a committed run_eval result file and update the "
        f"reference in {Path(__file__).name}."
    )


@pytest.mark.parametrize("case", CASES, ids=[c.label for c in CASES])
async def test_rank_quality_does_not_regress(case: RetrievalCase, tmp_path, monkeypatch):
    if case.embedding_provider != "development" and not MODEL_READY:
        pytest.skip(f"{case.label} needs the MiniLM model: run scripts/download_embedding_model.py")

    summary = await measure_retrieval(tmp_path, case, monkeypatch)

    assert summary.mrr.count > 0, "no answerable question was scored"
    assert summary.mrr.value >= case.reference_mrr - TOLERANCE, _report(summary, case)
    assert (
        summary.page_recall.value >= case.reference_page_recall - TOLERANCE
    ), _report(summary, case)
