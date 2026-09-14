from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    document_id: str
    document_title: str
    page_number: int
    chunk_id: str
    relevance_score: float
    section: str | None = None
    excerpt: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string")
    document_ids: list[str] | None = Field(None, description="Optional filter by document IDs")
    top_k: int = Field(5, ge=1, le=20, description="Number of results to retrieve")


class SearchResponse(BaseModel):
    query: str
    results: list[SourceReference]


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question for the research copilot")
    document_ids: list[str] | None = Field(None, description="Optional filter by document IDs")
    top_k: int = Field(5, ge=1, le=15, description="Number of source chunks to retrieve")


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceReference]
    has_sufficient_evidence: bool
    prompt_tokens: int = 0
    completion_tokens: int = 0
