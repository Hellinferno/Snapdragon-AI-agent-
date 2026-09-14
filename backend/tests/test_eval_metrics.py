"""Unit tests for the RAG evaluation metrics (backend/evaluation/metrics.py)."""

import random

import pytest

from evaluation.metrics import (
    GenerationSummary,
    Mean,
    Ratio,
    RetrievalSummary,
    answer_is_correct,
    judge_generation,
    judge_retrieval,
    parse_citations,
    percentile,
    validate_question,
)

BOOK = "Data Science for Business"
OTHER = "Some Other Book"


def _question(answerable=True, pages=(50,), evidence=None, keywords=None):
    return {
        "id": "T1",
        "category": "direct_factual",
        "question": "q",
        "answerable": answerable,
        "expected_sources": [{"document": BOOK, "pages": list(pages)}] if answerable else [],
        "evidence": evidence or [],
        "answer_keywords": keywords if keywords is not None else ([["crisp-dm"]] if answerable else []),
    }


def _chunk(page, text="", doc=BOOK):
    return {"document_title": doc, "page_number": page, "text": text}


# ---------------------------------------------------------------------------
# Ratio / Mean bounds
# ---------------------------------------------------------------------------


def test_ratio_is_none_when_nothing_is_eligible():
    assert Ratio().value is None
    assert Ratio().to_dict() == {"percent": None, "numerator": 0, "denominator": 0}


def test_ratio_rejects_numerator_above_denominator():
    with pytest.raises(ValueError):
        Ratio(numerator=4, denominator=1).value


def test_mean_rejects_out_of_range_scores():
    with pytest.raises(ValueError):
        Mean().add(1.5)


def test_every_summary_metric_is_bounded_over_random_runs():
    rng = random.Random(7)
    for _ in range(200):
        retrieval = RetrievalSummary()
        generation = GenerationSummary()
        for _ in range(rng.randint(0, 12)):
            answerable = rng.random() < 0.8
            pages = rng.sample(range(1, 20), rng.randint(1, 3))
            q = _question(answerable, pages=pages, evidence=["crisp-dm"] if rng.random() < 0.5 else None)
            chunks = [
                _chunk(rng.randint(1, 20), rng.choice(["", "the CRISP-DM process"]), rng.choice([BOOK, OTHER]))
                for _ in range(rng.randint(0, 5))
            ]
            answer = rng.choice([
                "Insufficient evidence in the indexed documents to answer this question.",
                f"CRISP-DM [Doc: {BOOK}, Page: {rng.randint(1, 20)}]",
                f"CRISP-DM [Doc: {OTHER}, Pages 3-5] [Source 1]",
                "CRISP-DM with no citation",
            ])
            if answerable:
                retrieval.add(judge_retrieval(q, chunks))
            generation.add(q, judge_generation(q, answer, chunks))

        payload = retrieval.to_dict() | generation.to_dict()["generation"] | generation.to_dict()["citation"]
        for name, metric in payload.items():
            if "percent" in metric and metric["percent"] is not None:
                assert 0.0 <= metric["percent"] <= 100.0, name
            if "mean" in metric and metric["mean"] is not None:
                assert 0.0 <= metric["mean"] <= 1.0, name


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def test_retrieval_hits_and_mrr_use_evidence_rank():
    q = _question(pages=(50, 51), evidence=["cross-industry standard process"])
    chunks = [
        _chunk(12, "unrelated"),
        _chunk(50, "page but no phrase"),
        _chunk(51, "the Cross-Industry Standard\nProcess for Data Mining"),
    ]
    j = judge_retrieval(q, chunks)
    assert j.doc_hit and j.page_hit and j.evidence_hit
    assert j.page_recall == 1.0
    assert j.first_relevant_rank == 3
    assert j.reciprocal_rank == pytest.approx(1 / 3)


def test_retrieval_wrong_page_is_a_miss():
    q = _question(pages=(50,), evidence=["crisp-dm"])
    j = judge_retrieval(q, [_chunk(49, "nothing"), _chunk(12, "nothing")])
    assert j.doc_hit and not j.page_hit and not j.evidence_hit
    assert j.page_recall == 0.0 and j.reciprocal_rank == 0.0


def test_retrieval_falls_back_to_page_relevance_without_evidence():
    j = judge_retrieval(_question(pages=(7,)), [_chunk(3), _chunk(7)])
    assert j.evidence_hit is None
    assert j.first_relevant_rank == 2


def test_normalize_text_repairs_pdf_hyphenation():
    from evaluation.metrics import normalize_text

    assert normalize_text("a super‐\nvised  problem") == "a supervised problem"
    assert normalize_text("strawberry Pop-\nTarts") == "strawberry pop-tarts"


def test_retrieval_title_match_is_exact_not_word_overlap():
    # The previous evaluator accepted any two shared words, e.g. "Data ... Business"
    j = judge_retrieval(_question(pages=(5,)), [_chunk(5, doc="Business Data Ethics")])
    assert not j.doc_hit and not j.page_hit


# ---------------------------------------------------------------------------
# Citations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "answer, expected",
    [
        (f"x [Doc: {BOOK}, Page: 50].", [(BOOK, 50)]),
        (f'x [Doc: "{BOOK}", Page 50, Section: "Results"].', [(BOOK, 50)]),
        (f"x [Doc: {BOOK}, Pages 50-52]", [(BOOK, 50), (BOOK, 51), (BOOK, 52)]),
        (f"x [Doc: {BOOK}, Pages: 50, 60 and 61]", [(BOOK, 50), (BOOK, 60), (BOOK, 61)]),
        (f'x [Source 2: "{BOOK}", Page 9]', [(BOOK, 9)]),
        ("x [Source 1]", [(None, None)]),
        ("no citation here", []),
    ],
)
def test_parse_citations_formats(answer, expected):
    assert [(c.document, c.page) for c in parse_citations(answer)] == expected


def test_index_only_citation_resolves_against_context_order():
    q = _question(pages=(50,))
    context = [_chunk(12), _chunk(50)]
    j = judge_generation(q, "CRISP-DM [Source 2]", context)
    assert j.citations == [(BOOK, 50)]
    assert j.cited_expected_page and j.grounded


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def test_citation_to_unretrieved_page_is_not_grounded():
    q = _question(pages=(50,))
    j = judge_generation(q, f"CRISP-DM [Doc: {BOOK}, Page: 50]", [_chunk(12)])
    assert j.cited_expected_page  # right page ...
    assert not j.grounded  # ... but it was never in the context, so the model did not read it
    assert j.faithful_citations == 0


def test_retrieved_but_uncited_page_does_not_count_as_page_accuracy():
    # The previous evaluator passed page accuracy whenever the page was merely retrieved
    q = _question(pages=(50,))
    j = judge_generation(q, "CRISP-DM is a process.", [_chunk(50)])
    assert not j.cited_expected_page and not j.grounded and j.citations == []


def test_refusal_on_answerable_question_is_false_refusal_not_abstention():
    summary = GenerationSummary()
    refusal = "Insufficient evidence in the indexed documents to answer this question."
    summary.add(_question(True), judge_generation(_question(True), refusal, []))
    summary.add(_question(False), judge_generation(_question(False), refusal, []))
    out = summary.to_dict()["generation"]
    assert out["false_refusal_rate"] == {"percent": 100.0, "numerator": 1, "denominator": 1}
    assert out["abstention_accuracy"] == {"percent": 100.0, "numerator": 1, "denominator": 1}
    assert out["answer_correctness"]["percent"] == 0.0
    # Refused answers are excluded from citation metrics rather than counted as passes
    assert out["groundedness"]["denominator"] == 0


def test_answer_keywords_require_every_group():
    groups = [["supervised"], ["unsupervised", "no target"]]
    assert answer_is_correct("Supervised learning has a target; unsupervised does not.", groups)
    assert not answer_is_correct("Supervised learning has a target.", groups)
    with pytest.raises(ValueError):
        answer_is_correct("anything", [])


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


def test_percentile_nearest_rank():
    assert percentile([], 95) is None
    assert percentile([5.0], 95) == 5.0
    values = list(range(1, 21))
    assert percentile(values, 95) == 19
    assert percentile(values, 50) == 10


@pytest.mark.parametrize(
    "mutation",
    [
        lambda q: q.pop("answerable"),
        lambda q: q.update(answer_keywords=[]),
        lambda q: q.update(expected_sources=[]),
        lambda q: q.update(expected_sources=[{"document": BOOK, "pages": []}]),
    ],
)
def test_validate_question_rejects_unscorable_entries(mutation):
    q = _question()
    mutation(q)
    with pytest.raises(ValueError):
        validate_question(q)


def test_validate_question_rejects_unanswerable_with_sources():
    q = _question(False)
    q["expected_sources"] = [{"document": BOOK, "pages": [1]}]
    with pytest.raises(ValueError):
        validate_question(q)
