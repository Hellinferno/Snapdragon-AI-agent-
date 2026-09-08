from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db_models import Chunk, Document
from app.providers.embedding_provider import embedding_provider
from app.providers.llm_provider import llm_provider
from app.providers.vector_store import SQLiteVectorStore
from app.schemas.rag import ChatResponse, SearchResponse, SourceReference
from app.services.context_builder import (
    GROUNDING_SYSTEM_PROMPT,
    build_context_block,
    build_rag_prompt,
)


class RetrievalService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.vector_store = SQLiteVectorStore(db)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
        min_score: float = 0.05,
    ) -> SearchResponse:
        """Retrieves top-k source-aware chunks matching query."""
        query_vec = await embedding_provider.embed_text(query)
        scored_pairs = await self.vector_store.search(
            query_vector=query_vec,
            top_k=top_k,
            document_ids=document_ids,
        )

        if not scored_pairs:
            return SearchResponse(query=query, results=[])

        # Filter by minimum similarity score
        valid_pairs = [p for p in scored_pairs if p[1] >= min_score]
        if not valid_pairs:
            return SearchResponse(query=query, results=[])

        chunk_ids = [cid for cid, _ in valid_pairs]
        score_map = dict(valid_pairs)

        # Load chunks with related Document and Page
        stmt = (
            select(Chunk)
            .where(Chunk.id.in_(chunk_ids))
            .options(selectinload(Chunk.document), selectinload(Chunk.page))
        )
        res = await self.db.execute(stmt)
        chunks = res.scalars().all()

        # Map back to ordered results
        chunk_lookup = {c.id: c for c in chunks}
        sources: list[SourceReference] = []

        for cid, score in valid_pairs:
            chunk = chunk_lookup.get(cid)
            if not chunk:
                continue

            doc_title = chunk.document.title or chunk.document.filename if chunk.document else "Untitled Document"
            page_num = chunk.page.page_number if chunk.page else 1

            sources.append(
                SourceReference(
                    document_id=chunk.document_id,
                    document_title=doc_title,
                    page_number=page_num,
                    chunk_id=chunk.id,
                    relevance_score=score,
                    section=chunk.section,
                    excerpt=chunk.text,
                )
            )

        return SearchResponse(query=query, results=sources)

    async def chat(
        self,
        question: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
        min_score_threshold: float = 0.08,
    ) -> ChatResponse:
        """
        Executes grounded question answering.
        Retrieves relevant sources, synthesizes an answer, and flags insufficient evidence.
        """
        search_res = await self.search(
            query=question,
            top_k=top_k,
            document_ids=document_ids,
            min_score=min_score_threshold,
        )

        sources = search_res.results
        has_sufficient = len(sources) > 0 and sources[0].relevance_score >= min_score_threshold

        if not has_sufficient:
            context_block = "NO_RELEVANT_EVIDENCE"
        else:
            context_block = build_context_block(sources)

        prompt = build_rag_prompt(question, context_block)
        gen_result = await llm_provider.generate(prompt, system_prompt=GROUNDING_SYSTEM_PROMPT)

        return ChatResponse(
            question=question,
            answer=gen_result.text,
            sources=sources if has_sufficient else [],
            has_sufficient_evidence=has_sufficient,
        )
