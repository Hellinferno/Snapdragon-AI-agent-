"""Evidence-based cross-paper comparison.

Every statement in a comparison is extracted verbatim from an indexed passage and
carries its page citation; nothing is generated. A dimension a paper does not
address is reported as an evidence gap instead of being filled with a guess.
"""

import re
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Document
from app.schemas.rag import SourceReference
from app.schemas.research import (
    ComparisonCell,
    CompareResponse,
    CriterionEvidence,
    CriterionMatch,
    DocumentComparisonItem,
    EvidenceGap,
)
from app.services.retrieval_service import RetrievalService


@dataclass(frozen=True)
class DimensionSpec:
    """How to find a paper's evidence for one comparison dimension.

    Three transparent signals, in order of strength:

    * ``sections`` — the section label or heading the dimension usually lives
      under (a passage headed "Limitations" is the limitations evidence);
    * ``cues`` — the explicit vocabulary a passage must use to count at all, so a
      paper that never discusses (say) its dataset is reported as a gap rather
      than having its closest passage quoted as if it answered;
    * ``query`` — semantic similarity, used only to order otherwise equal passages.
    """

    query: str
    cues: str
    sections: str


DIMENSION_SPECS: dict[str, DimensionSpec] = {
    "Research Objective": DimensionSpec(
        "the aim of this study: what it investigates, explores or proposes",
        r"\b(investigat|aims?\b|objective|goal|propos|explores?|assess|examin|purpose|this (study|paper|work))",
        r"abstract|introduction|objective|aims?\b",
    ),
    "Methodology": DimensionSpec(
        "methodology: the study design, approach and procedure used",
        r"\b(method|approach|procedure|protocol|study design|double-blind|randomi[sz]|evaluated|experiment|implemented|constructs?)",
        r"method|materials|approach|experiment|study design|system design",
    ),
    "Dataset": DimensionSpec(
        "dataset: the data, cohort, participants or samples the study used",
        r"\b(datasets?|data set|corpus|cohorts?|participants|subjects|trained on|collected|x-rays?|across \d[\d,]*)\b"
        r"|\b\d[\d,]*\s+(?:[a-z-]+\s+)?(patients|participants|residents|students|samples|images|scans|summaries|records|subjects|documents)\b",
        r"data|method|materials|experiment|finding|result|evaluation",
    ),
    "Model / Architecture": DimensionSpec(
        "model architecture: the neural network, backbone or system design",
        r"\b(model|architecture|backbone|transformers?|neural network|encoder|decoder|layers?|quantiz|int4|4-bit|parameters)",
        r"architecture|method|model|system design",
    ),
    "Metrics": DimensionSpec(
        "evaluation metrics measured: accuracy, AUC, precision, recall, latency, error rate",
        r"(\b(accuracy|auc|precision|recall|f1|sensitivity|specificity|latency|throughput|error|scores?|retention)\b|\d+(\.\d+)?\s*(%|ms\b))",
        r"finding|result|evaluation|experiment|metric",
    ),
    "Results": DimensionSpec(
        "results: the main findings and reported outcomes",
        r"\b(achiev|results?\b|findings?\b|found\b|showed|improv|reduc|increas|outperform|demonstrat)",
        r"finding|result|evaluation|experiment",
    ),
    "Limitations": DimensionSpec(
        "limitations, constraints and future work",
        r"\b(limitations?|limited|constraints?|future work|remains?|requires?|relies|undersampled|drawbacks?|however|cannot|not yet)\b",
        r"limitation|discussion|future work|conclusion",
    ),
    "Trade-offs": DimensionSpec(
        "trade-offs: what is gained at the cost of what, overhead or compromise",
        r"\b(trade-?offs?|at the (cost|expense)|overhead|compromis|penalt|in exchange for)",
        r"discussion|limitation|trade",
    ),
}

DEFAULT_DIMENSIONS = list(DIMENSION_SPECS)

# Passages considered per (paper, dimension). Scoped to one paper, so this covers
# every chunk of a typical paper at negligible cost.
CANDIDATES_PER_DIMENSION = 12
# Minimum similarity gap between the two closest papers before one is named the
# better match for a criterion; smaller gaps are reported as "no clear difference".
CRITERION_MARGIN = 0.05
MAX_STATEMENT_CHARS = 320

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _cue_pattern(dimension: str) -> re.Pattern[str] | None:
    spec = DIMENSION_SPECS.get(dimension)
    if spec is not None:
        return re.compile(spec.cues, re.IGNORECASE)
    # Custom dimension: its own content words (5-letter stems) are the vocabulary.
    stems = [w[:5] for w in re.findall(r"[a-zA-Z]{4,}", dimension)]
    if not stems:
        return None
    return re.compile(r"\b(" + "|".join(re.escape(s) for s in stems) + ")", re.IGNORECASE)


def _section_pattern(dimension: str) -> re.Pattern[str] | None:
    spec = DIMENSION_SPECS.get(dimension)
    return re.compile(spec.sections, re.IGNORECASE) if spec is not None else _cue_pattern(dimension)


def _heading(excerpt: str) -> str:
    """The passage's leading heading line, if it has one."""
    lines = [line.strip() for line in excerpt.strip().splitlines() if line.strip()]
    if len(lines) > 1 and len(lines[0]) <= 60 and not lines[0].endswith("."):
        return lines[0]
    return ""


def _body_sentences(excerpt: str) -> list[str]:
    """Split a passage into sentences, dropping a leading section-heading line."""
    lines = [line.strip() for line in excerpt.strip().splitlines() if line.strip()]
    if _heading(excerpt):
        lines = lines[1:]
    body = " ".join(lines)
    return [s.strip() for s in SENTENCE_SPLIT.split(body) if s.strip()]


def extract_statement(excerpt: str, cues: re.Pattern[str] | None) -> str:
    """The sentence of ``excerpt`` that states the dimension, quoted verbatim."""
    sentences = _body_sentences(excerpt)
    if not sentences:
        return excerpt.strip()[:MAX_STATEMENT_CHARS]
    chosen = next((s for s in sentences if cues is not None and cues.search(s)), sentences[0])
    if len(chosen) > MAX_STATEMENT_CHARS:
        chosen = chosen[: MAX_STATEMENT_CHARS - 1].rstrip() + "…"
    return chosen


def citation_tag(source: SourceReference) -> str:
    return f'[Doc: "{source.document_title}", Page {source.page_number}]'


class ComparisonService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.retrieval_service = RetrievalService(db)

    async def compare_documents(
        self,
        document_ids: list[str],
        dimensions: list[str] | None = None,
        criteria: list[str] | None = None,
    ) -> CompareResponse:
        """Compares papers dimension by dimension using only quoted, cited evidence."""
        if len(document_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least two documents are required for comparison.",
            )

        active_dimensions = [d.strip() for d in (dimensions or []) if d and d.strip()] or DEFAULT_DIMENSIONS
        active_criteria = [c.strip() for c in (criteria or []) if c and c.strip()]

        res = await self.db.execute(select(Document).where(Document.id.in_(document_ids)))
        doc_map = {d.id: d for d in res.scalars().all()}
        missing = [did for did in document_ids if did not in doc_map]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documents not found: {', '.join(missing)}",
            )
        titles = {did: doc_map[did].title or doc_map[did].filename for did in document_ids}

        comparisons: list[DocumentComparisonItem] = []
        gaps: list[EvidenceGap] = []
        all_sources: list[SourceReference] = []

        for doc_id in document_ids:
            cells: dict[str, ComparisonCell] = {}
            for dim in active_dimensions:
                cell = await self._find_evidence(doc_id, dim)
                cells[dim] = cell
                if cell.source is None:
                    gaps.append(
                        EvidenceGap(
                            document_id=doc_id,
                            document_title=titles[doc_id],
                            dimension=dim,
                            note=cell.statement,
                        )
                    )
                elif all(s.chunk_id != cell.source.chunk_id for s in all_sources):
                    all_sources.append(cell.source)

            comparisons.append(
                DocumentComparisonItem(
                    document_id=doc_id,
                    document_title=titles[doc_id],
                    dimension_values={
                        dim: f"{c.statement} {citation_tag(c.source)}" if c.source else c.statement
                        for dim, c in cells.items()
                    },
                    cells=cells,
                    evidence=[c.source for c in cells.values() if c.source is not None],
                )
            )

        criterion_matches = [
            await self._match_criterion(criterion, document_ids, titles) for criterion in active_criteria
        ]

        return CompareResponse(
            dimensions=active_dimensions,
            comparisons=comparisons,
            synthesis=self._build_synthesis(comparisons, active_dimensions),
            all_sources=all_sources,
            evidence_gaps=gaps,
            criterion_matches=criterion_matches,
        )

    async def _find_evidence(self, doc_id: str, dimension: str) -> ComparisonCell:
        """The passage of ``doc_id`` that most directly addresses ``dimension``.

        Only passages using the dimension's vocabulary (in their section label,
        heading or text) qualify; among those, one filed under the dimension's usual
        section wins, and semantic rank breaks the remaining ties.
        """
        spec = DIMENSION_SPECS.get(dimension)
        cues = _cue_pattern(dimension)
        sections = _section_pattern(dimension)
        search_res = await self.retrieval_service.search(
            query=spec.query if spec else dimension,
            top_k=CANDIDATES_PER_DIMENSION,
            document_ids=[doc_id],
            min_score=-1.0,  # rank every passage of the paper; the cue check filters
        )
        qualifying = [
            c
            for c in search_res.results
            if cues is None or cues.search(f"{c.section or ''}\n{c.excerpt}")
        ]
        if qualifying:
            in_section = [
                c
                for c in qualifying
                if sections is not None and sections.search(f"{c.section or ''}\n{_heading(c.excerpt)}")
            ]
            best = (in_section or qualifying)[0]
            return ComparisonCell(
                dimension=dimension,
                reported=True,
                statement=extract_statement(best.excerpt, cues),
                source=best,
            )
        return ComparisonCell(
            dimension=dimension,
            reported=False,
            statement=f"Not reported: no indexed passage of this paper explicitly addresses {dimension.lower()}.",
        )

    async def _match_criterion(
        self, criterion: str, document_ids: list[str], titles: dict[str, str]
    ) -> CriterionMatch:
        """Which paper's closest passage is most similar to ``criterion``.

        This measures how directly each paper addresses the criterion, not which
        paper is better; the evidence and scores are returned so a reader can judge.
        """
        evidence: list[CriterionEvidence] = []
        for doc_id in document_ids:
            res = await self.retrieval_service.search(
                query=criterion, top_k=1, document_ids=[doc_id], min_score=0.01
            )
            top = res.results[0] if res.results else None
            evidence.append(
                CriterionEvidence(
                    document_id=doc_id,
                    document_title=titles[doc_id],
                    relevance_score=top.relevance_score if top else 0.0,
                    source=top,
                )
            )
        evidence.sort(key=lambda e: e.relevance_score, reverse=True)

        found = [e for e in evidence if e.source is not None]
        if not found:
            return CriterionMatch(
                criterion=criterion,
                verdict="No passage in any selected paper relates to this criterion.",
                evidence=evidence,
            )

        best = found[0]
        runner_up = found[1].relevance_score if len(found) > 1 else 0.0
        if best.relevance_score - runner_up < CRITERION_MARGIN:
            return CriterionMatch(
                criterion=criterion,
                verdict=(
                    f"No clear difference: the closest passages score within {CRITERION_MARGIN:.2f} "
                    f"of each other ({best.relevance_score:.2f} vs {runner_up:.2f})."
                ),
                evidence=evidence,
            )
        return CriterionMatch(
            criterion=criterion,
            better_match_document_id=best.document_id,
            better_match_document_title=best.document_title,
            verdict=(
                f'"{best.document_title}" addresses this criterion more directly '
                f"(similarity {best.relevance_score:.2f} vs {runner_up:.2f})."
            ),
            evidence=evidence,
        )

    def _build_synthesis(
        self,
        comparisons: list[DocumentComparisonItem],
        dimensions: list[str],
    ) -> str:
        """Plain-text summary of what the evidence covers; it asserts nothing about the papers."""
        titles_str = " and ".join(f'"{c.document_title}"' for c in comparisons)
        total = len(comparisons) * len(dimensions)
        reported = sum(
            1
            for c in comparisons
            for dim in dimensions
            if (cell := c.cells.get(dim)) is not None and cell.reported
        )
        if reported == 0:
            return (
                f"Evidence-based comparison of {len(comparisons)} papers ({titles_str}): "
                "No source-backed comparison evidence was retrieved for the selected dimensions."
            )

        unaddressed = [
            dim
            for dim in dimensions
            if not any((cell := c.cells.get(dim)) is not None and cell.reported for c in comparisons)
        ]
        summary = (
            f"Evidence-based comparison of {len(comparisons)} papers ({titles_str}) across "
            f"{len(dimensions)} dimensions: {reported} of {total} cells quote a cited passage; "
            f"{total - reported} are evidence gaps."
        )
        if unaddressed:
            summary += f" No selected paper explicitly addresses: {', '.join(unaddressed)}."
        return summary
