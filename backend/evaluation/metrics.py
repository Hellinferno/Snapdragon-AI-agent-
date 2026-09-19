"""Pure scoring functions for the ScholarEdge RAG evaluation.

No I/O and no app imports, so every metric can be unit-tested in isolation.

Metrics are split into three independent groups:

Retrieval (answerable questions only, measured before any score threshold or LLM):
    doc_hit@k        an expected document appears in the top-k chunks
    page_hit@k       an expected (document, page) appears in the top-k chunks
    page_recall@k    fraction of expected (document, page) pairs found in the top-k
    evidence_hit@k   a top-k chunk contains one of the question's evidence phrases
    mrr              reciprocal rank of the first relevant chunk (evidence, else page)
    precision@k      fraction of the k retrieved slots that were relevant

Generation:
    answer_correctness   answerable questions whose answer contains every required fact
    false_refusal_rate   answerable questions the system refused
    abstention_accuracy  unanswerable questions the system refused
    groundedness         answered questions with >=1 citation, all pointing at retrieved pages

Citation (parsed from the answer text only; retrieval is never used as a fallback):
    citation_rate        answered questions containing >=1 parseable citation
    cited_page_accuracy  answered questions citing >=1 expected page
    cited_doc_accuracy   citations naming an expected document (micro-averaged)
    citation_faithfulness citations whose (document, page) was in the retrieved context

Every rate is a Ratio with an explicit numerator and denominator; its value is None when
nothing was eligible, never a fabricated 100%.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

REFUSAL_PHRASE = "insufficient evidence"


# ---------------------------------------------------------------------------
# Aggregates
# ---------------------------------------------------------------------------


@dataclass
class Ratio:
    numerator: int = 0
    denominator: int = 0

    def add(self, hit: bool) -> None:
        self.numerator += int(bool(hit))
        self.denominator += 1

    @property
    def value(self) -> float | None:
        if self.numerator < 0 or self.numerator > self.denominator:
            raise ValueError(f"Invalid ratio {self.numerator}/{self.denominator}")
        if self.denominator == 0:
            return None
        return 100.0 * self.numerator / self.denominator

    def to_dict(self) -> dict:
        v = self.value
        return {
            "percent": None if v is None else round(v, 2),
            "numerator": self.numerator,
            "denominator": self.denominator,
        }


@dataclass
class Mean:
    """Mean of per-question scores that each lie in [0, 1]."""

    total: float = 0.0
    count: int = 0

    def add(self, score: float) -> None:
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Score {score} outside [0, 1]")
        self.total += score
        self.count += 1

    @property
    def value(self) -> float | None:
        return None if self.count == 0 else self.total / self.count

    def to_dict(self) -> dict:
        v = self.value
        return {"mean": None if v is None else round(v, 4), "count": self.count}


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Lowercase, repair PDF line-break hyphenation, collapse whitespace.

    Typeset PDFs mark soft line-break hyphens with U+2010 or U+00AD ("super‐\\nvised"),
    which are joined; an ASCII hyphen before a line break is a real hyphen ("Pop-\\nTarts").
    """
    text = re.sub(r"(\w)[‐­]\s*\n\s*(\w)", r"\1\2", text)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1-\2", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def titles_match(expected: str, actual: str) -> bool:
    return bool(expected) and normalize_title(expected) == normalize_title(actual)


def is_refusal(answer: str) -> bool:
    return REFUSAL_PHRASE in answer.lower()


def expected_pairs(expected_sources: list[dict]) -> set[tuple[str, int]]:
    return {
        (normalize_title(src["document"]), int(page))
        for src in expected_sources
        for page in src.get("pages", [])
    }


# ---------------------------------------------------------------------------
# Citation parsing
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Citation:
    document: str | None  # None when the citation only names a source index
    page: int | None
    source_index: int | None = None


_BRACKET = re.compile(r"\[((?:Doc|Source)\b[^\]]*)\]", re.IGNORECASE)
_PAGES = re.compile(r"\bPages?\s*:?\s*(\d+(?:\s*(?:,|-|–|and|&)\s*\d+)*)", re.IGNORECASE)
_DOC_TITLE = re.compile(r"^Doc\s*:\s*(.+?)(?:,\s*Pages?\b|,\s*Section\b|$)", re.IGNORECASE)
_SOURCE = re.compile(r"^Source\s+(\d+)\s*(?::\s*(.+?))?(?:,\s*Pages?\b|,\s*Section\b|$)", re.IGNORECASE)


def _expand_pages(spec: str) -> list[int]:
    pages: list[int] = []
    for part in re.split(r"\s*(?:,|and|&)\s*", spec):
        if not part:
            continue
        bounds = re.split(r"\s*[-–]\s*", part)
        if len(bounds) == 2 and bounds[0].isdigit() and bounds[1].isdigit():
            lo, hi = int(bounds[0]), int(bounds[1])
            if lo <= hi and hi - lo <= 20:
                pages.extend(range(lo, hi + 1))
                continue
        pages.extend(int(b) for b in bounds if b.isdigit())
    return pages


def parse_citations(answer: str) -> list[Citation]:
    """Extracts citations such as [Doc: Title, Page: 4], [Doc: "Title", Pages 4-5]
    and [Source 2: "Title", Page 4] from an answer."""
    citations: list[Citation] = []
    for match in _BRACKET.finditer(answer):
        body = match.group(1).strip()
        title: str | None = None
        index: int | None = None

        doc_match = _DOC_TITLE.match(body)
        src_match = _SOURCE.match(body)
        if doc_match:
            title = doc_match.group(1)
        elif src_match:
            index = int(src_match.group(1))
            title = src_match.group(2)
        if title is not None:
            title = title.strip().strip("\"'“”").strip() or None

        page_match = _PAGES.search(body)
        pages = _expand_pages(page_match.group(1)) if page_match else []
        if pages:
            citations.extend(Citation(title, p, index) for p in pages)
        else:
            citations.append(Citation(title, None, index))
    return citations


def resolve_citation(citation: Citation, retrieved: list[dict]) -> tuple[str | None, int | None]:
    """Fills document/page for index-only citations like [Source 2] from the context order."""
    doc, page = citation.document, citation.page
    if citation.source_index is not None and 1 <= citation.source_index <= len(retrieved):
        src = retrieved[citation.source_index - 1]
        doc = doc or src["document_title"]
        page = page if page is not None else src["page_number"]
    return doc, page


# ---------------------------------------------------------------------------
# Per-question judgments
# ---------------------------------------------------------------------------


def chunk_contains_evidence(chunk_text: str, evidence: list[str]) -> bool:
    haystack = normalize_text(chunk_text)
    return any(normalize_text(phrase) in haystack for phrase in evidence)


@dataclass
class RetrievalJudgment:
    doc_hit: bool
    page_hit: bool
    page_recall: float
    evidence_hit: bool | None  # None when the question lists no evidence phrases
    reciprocal_rank: float
    first_relevant_rank: int | None
    # Fraction of the retrieved slots that were relevant. Unlike hit@k this falls
    # when a change floods the top-k with redundant or off-topic chunks, so it is
    # the metric that notices a precision-for-recall trade.
    precision: float = 0.0


def judge_retrieval(question: dict, retrieved: list[dict]) -> RetrievalJudgment:
    """retrieved: ordered chunks with document_title, page_number and text."""
    expected = expected_pairs(question["expected_sources"])
    expected_docs = {doc for doc, _ in expected} | {
        normalize_title(s["document"]) for s in question["expected_sources"]
    }
    evidence = question.get("evidence") or []

    found_pairs: set[tuple[str, int]] = set()
    doc_hit = False
    evidence_hit = False
    first_rank: int | None = None

    relevant_slots = 0
    for rank, chunk in enumerate(retrieved, 1):
        pair = (normalize_title(chunk["document_title"]), int(chunk["page_number"]))
        doc_hit = doc_hit or pair[0] in expected_docs
        on_page = pair in expected
        if on_page:
            found_pairs.add(pair)
        has_evidence = bool(evidence) and chunk_contains_evidence(chunk.get("text", ""), evidence)
        evidence_hit = evidence_hit or has_evidence
        relevant = has_evidence if evidence else on_page
        if relevant:
            relevant_slots += 1
        if relevant and first_rank is None:
            first_rank = rank

    return RetrievalJudgment(
        doc_hit=doc_hit,
        page_hit=bool(found_pairs),
        page_recall=len(found_pairs) / len(expected) if expected else 0.0,
        evidence_hit=evidence_hit if evidence else None,
        reciprocal_rank=1.0 / first_rank if first_rank else 0.0,
        first_relevant_rank=first_rank,
        precision=relevant_slots / len(retrieved) if retrieved else 0.0,
    )


def answer_is_correct(answer: str, answer_keywords: list[list[str]]) -> bool:
    """Every keyword group must be satisfied by at least one of its alternatives."""
    if not answer_keywords:
        raise ValueError("Answerable questions need answer_keywords to judge correctness")
    text = normalize_text(answer)
    return all(any(normalize_text(alt) in text for alt in group) for group in answer_keywords)


@dataclass
class GenerationJudgment:
    refused: bool
    correct: bool | None  # None for unanswerable questions
    citations: list[tuple[str | None, int | None]] = field(default_factory=list)
    cited_expected_page: bool = False
    cited_expected_docs: int = 0
    faithful_citations: int = 0

    @property
    def grounded(self) -> bool:
        return bool(self.citations) and self.faithful_citations == len(self.citations)


def judge_generation(question: dict, answer: str, context: list[dict]) -> GenerationJudgment:
    """context: the chunks actually passed to the LLM (in prompt order)."""
    refused = is_refusal(answer)
    if not question["answerable"]:
        return GenerationJudgment(refused=refused, correct=None)

    expected = expected_pairs(question["expected_sources"])
    expected_docs = {normalize_title(s["document"]) for s in question["expected_sources"]}
    context_pairs = {(normalize_title(c["document_title"]), int(c["page_number"])) for c in context}
    context_docs = {doc for doc, _ in context_pairs}

    resolved = [resolve_citation(c, context) for c in parse_citations(answer)]
    cited_expected_page = False
    cited_expected_docs = 0
    faithful = 0

    for doc, page in resolved:
        # A citation without a title can only refer to a document when the context holds one
        doc_key = normalize_title(doc) if doc else (next(iter(context_docs)) if len(context_docs) == 1 else None)
        if doc_key in expected_docs:
            cited_expected_docs += 1
        if doc_key is not None and page is not None:
            if (doc_key, page) in expected:
                cited_expected_page = True
            if (doc_key, page) in context_pairs:
                faithful += 1

    return GenerationJudgment(
        refused=refused,
        correct=(not refused) and answer_is_correct(answer, question["answer_keywords"]),
        citations=resolved,
        cited_expected_page=cited_expected_page,
        cited_expected_docs=cited_expected_docs,
        faithful_citations=faithful,
    )


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100.0 * len(ordered)))
    return ordered[rank - 1]


@dataclass
class RetrievalSummary:
    doc_hit: Ratio = field(default_factory=Ratio)
    page_hit: Ratio = field(default_factory=Ratio)
    evidence_hit: Ratio = field(default_factory=Ratio)
    page_recall: Mean = field(default_factory=Mean)
    mrr: Mean = field(default_factory=Mean)
    precision: Mean = field(default_factory=Mean)

    def add(self, j: RetrievalJudgment) -> None:
        self.doc_hit.add(j.doc_hit)
        self.page_hit.add(j.page_hit)
        if j.evidence_hit is not None:
            self.evidence_hit.add(j.evidence_hit)
        self.page_recall.add(j.page_recall)
        self.mrr.add(j.reciprocal_rank)
        self.precision.add(j.precision)

    def to_dict(self) -> dict:
        return {
            "doc_hit_at_k": self.doc_hit.to_dict(),
            "page_hit_at_k": self.page_hit.to_dict(),
            "evidence_hit_at_k": self.evidence_hit.to_dict(),
            "page_recall_at_k": self.page_recall.to_dict(),
            "mrr": self.mrr.to_dict(),
            "precision_at_k": self.precision.to_dict(),
        }


@dataclass
class GenerationSummary:
    answer_correctness: Ratio = field(default_factory=Ratio)
    false_refusal_rate: Ratio = field(default_factory=Ratio)
    abstention_accuracy: Ratio = field(default_factory=Ratio)
    groundedness: Ratio = field(default_factory=Ratio)
    citation_rate: Ratio = field(default_factory=Ratio)
    cited_page_accuracy: Ratio = field(default_factory=Ratio)
    cited_doc_accuracy: Ratio = field(default_factory=Ratio)
    citation_faithfulness: Ratio = field(default_factory=Ratio)

    def add(self, question: dict, j: GenerationJudgment) -> None:
        if not question["answerable"]:
            self.abstention_accuracy.add(j.refused)
            return
        self.answer_correctness.add(bool(j.correct))
        self.false_refusal_rate.add(j.refused)
        if j.refused:
            return
        self.groundedness.add(j.grounded)
        self.citation_rate.add(bool(j.citations))
        self.cited_page_accuracy.add(j.cited_expected_page)
        self.cited_doc_accuracy.numerator += j.cited_expected_docs
        self.cited_doc_accuracy.denominator += len(j.citations)
        self.citation_faithfulness.numerator += j.faithful_citations
        self.citation_faithfulness.denominator += len(j.citations)

    def to_dict(self) -> dict:
        return {
            "generation": {
                "answer_correctness": self.answer_correctness.to_dict(),
                "false_refusal_rate": self.false_refusal_rate.to_dict(),
                "abstention_accuracy": self.abstention_accuracy.to_dict(),
                "groundedness": self.groundedness.to_dict(),
            },
            "citation": {
                "citation_rate": self.citation_rate.to_dict(),
                "cited_page_accuracy": self.cited_page_accuracy.to_dict(),
                "cited_doc_accuracy": self.cited_doc_accuracy.to_dict(),
                "citation_faithfulness": self.citation_faithfulness.to_dict(),
            },
        }


def validate_question(question: dict) -> None:
    """Fails fast on dataset entries that would make a metric meaningless."""
    qid = question.get("id", "?")
    for key in ("id", "category", "question", "answerable", "expected_sources"):
        if key not in question:
            raise ValueError(f"{qid}: missing '{key}'")
    if question["answerable"]:
        if not question["expected_sources"]:
            raise ValueError(f"{qid}: answerable question without expected_sources")
        if not question.get("answer_keywords"):
            raise ValueError(f"{qid}: answerable question without answer_keywords")
        for src in question["expected_sources"]:
            if not src.get("pages"):
                raise ValueError(f"{qid}: expected source without pages")
    elif question["expected_sources"]:
        raise ValueError(f"{qid}: unanswerable question must not list expected_sources")
