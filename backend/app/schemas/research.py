from typing import Literal

from pydantic import BaseModel, Field
from app.schemas.rag import SourceReference


class CompareRequest(BaseModel):
    document_ids: list[str] = Field(
        ...,
        min_length=2,
        description="List of at least two document IDs to compare",
    )
    dimensions: list[str] | None = Field(
        default=None,
        description="Optional list of comparison dimensions (e.g. Methodology, Dataset, Limitations)",
    )
    criteria: list[str] | None = Field(
        default=None,
        max_length=5,
        description=(
            "Optional free-text criteria (e.g. 'on-device deployment'). For each one the "
            "response reports which paper's text addresses it most directly, with evidence."
        ),
    )


class ComparisonCell(BaseModel):
    """One paper's evidence for one dimension: a verbatim statement plus its source."""

    dimension: str
    reported: bool
    statement: str
    source: SourceReference | None = None


class DocumentComparisonItem(BaseModel):
    document_id: str
    document_title: str
    # Statement + citation tag per dimension, as plain text.
    dimension_values: dict[str, str]
    cells: dict[str, ComparisonCell] = {}
    evidence: list[SourceReference] = []


class EvidenceGap(BaseModel):
    document_id: str
    document_title: str
    dimension: str
    note: str


class CriterionEvidence(BaseModel):
    document_id: str
    document_title: str
    relevance_score: float
    source: SourceReference | None = None


class CriterionMatch(BaseModel):
    """Which paper's text addresses a criterion most directly, and the evidence for it."""

    criterion: str
    better_match_document_id: str | None = None
    better_match_document_title: str | None = None
    verdict: str
    evidence: list[CriterionEvidence]


class CompareResponse(BaseModel):
    dimensions: list[str]
    comparisons: list[DocumentComparisonItem]
    synthesis: str
    all_sources: list[SourceReference]
    evidence_gaps: list[EvidenceGap] = []
    criterion_matches: list[CriterionMatch] = []
    method: Literal["extractive"] = "extractive"
