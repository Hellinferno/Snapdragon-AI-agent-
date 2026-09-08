from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db_models import Document
from app.schemas.rag import SourceReference
from app.schemas.research import CompareResponse, DocumentComparisonItem
from app.services.retrieval_service import RetrievalService

DEFAULT_DIMENSIONS = [
    "Core Objective",
    "Methodology & Architecture",
    "Key Findings & Metrics",
    "Limitations & Future Work",
]


class ComparisonService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.retrieval_service = RetrievalService(db)

    async def compare_documents(
        self,
        document_ids: list[str],
        dimensions: list[str] | None = None,
    ) -> CompareResponse:
        """
        Executes multi-document comparative analysis across specified dimensions.
        Preserves source references and provides cross-paper synthesis.
        """
        if len(document_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least two documents are required for comparison.",
            )

        active_dimensions = dimensions if dimensions and len(dimensions) > 0 else DEFAULT_DIMENSIONS

        # Fetch requested documents
        stmt = (
            select(Document)
            .where(Document.id.in_(document_ids))
            .options(selectinload(Document.pages), selectinload(Document.chunks))
        )
        res = await self.db.execute(stmt)
        docs = res.scalars().all()
        doc_map = {d.id: d for d in docs}

        # Check that all requested documents exist
        missing = [did for did in document_ids if did not in doc_map]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documents not found: {', '.join(missing)}",
            )

        comparisons: list[DocumentComparisonItem] = []
        all_sources: list[SourceReference] = []

        # Analyze each document across dimensions
        for doc_id in document_ids:
            doc = doc_map[doc_id]
            doc_title = doc.title or doc.filename
            dim_values: dict[str, str] = {}
            doc_evidence: list[SourceReference] = []

            for dim in active_dimensions:
                # Query retrieval service scoped to this single document
                search_res = await self.retrieval_service.search(
                    query=f"{doc_title} {dim}",
                    top_k=2,
                    document_ids=[doc_id],
                    min_score=0.01,
                )

                if search_res.results:
                    top_hit = search_res.results[0]
                    clean_excerpt = top_hit.excerpt.replace("\n", " ").strip()
                    sentences = [s.strip() for s in clean_excerpt.split(". ") if len(s.strip()) > 10]
                    summary_text = ". ".join(sentences[:2])
                    if summary_text and not summary_text.endswith("."):
                        summary_text += "."

                    citation_tag = f"[Doc: \"{doc_title}\", Page {top_hit.page_number}]"
                    dim_values[dim] = f"{summary_text} {citation_tag}"
                    doc_evidence.append(top_hit)
                    all_sources.append(top_hit)
                else:
                    dim_values[dim] = f"No explicit details found for {dim} in indexed sections."

            comparisons.append(
                DocumentComparisonItem(
                    document_id=doc.id,
                    document_title=doc_title,
                    dimension_values=dim_values,
                    evidence=doc_evidence,
                )
            )

        # Generate comparative synthesis narrative
        synthesis = self._build_synthesis(comparisons, active_dimensions)

        return CompareResponse(
            dimensions=active_dimensions,
            comparisons=comparisons,
            synthesis=synthesis,
            all_sources=all_sources,
        )

    def _build_synthesis(
        self,
        comparisons: list[DocumentComparisonItem],
        dimensions: list[str],
    ) -> str:
        """Synthesizes cross-paper commonalities and divergences."""
        titles = [f'"{c.document_title}"' for c in comparisons]
        titles_str = " and ".join(titles)

        paragraphs: list[str] = []
        paragraphs.append(
            f"Cross-Paper Comparative Analysis across {len(comparisons)} documents ({titles_str}):\n"
        )

        for dim in dimensions:
            dim_points: list[str] = []
            for item in comparisons:
                val = item.dimension_values.get(dim, "")
                if "No explicit details" not in val:
                    dim_points.append(f"• In \"{item.document_title}\": {val}")

            if dim_points:
                paragraphs.append(f"### {dim}\n" + "\n".join(dim_points))

        if len(paragraphs) == 1:
            paragraphs.append(
                "No source-backed comparison evidence was retrieved for the selected dimensions."
            )
        else:
            paragraphs.append(
                "### Evidence-Based Summary\n"
                "The cited excerpts above are the available comparison evidence; no additional conclusion is inferred."
            )

        return "\n\n".join(paragraphs)
