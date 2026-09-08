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
        description="Optional list of comparison dimensions (e.g. Methodology, Findings, Limitations)",
    )


class DocumentComparisonItem(BaseModel):
    document_id: str
    document_title: str
    dimension_values: dict[str, str]
    evidence: list[SourceReference] = []


class CompareResponse(BaseModel):
    dimensions: list[str]
    comparisons: list[DocumentComparisonItem]
    synthesis: str
    all_sources: list[SourceReference]
