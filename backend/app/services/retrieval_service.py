from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db_models import Chunk, Document
from app.providers.base import EmbeddingProvider, LLMProvider
from app.providers.factory import get_embedding_provider, get_llm_provider
from app.providers.vector_store import SQLiteVectorStore
from app.services.lexical_index import get_bm25_index
from app.schemas.rag import ChatResponse, SearchResponse, SourceReference
from app.services.context_builder import (
    GROUNDING_SYSTEM_PROMPT,
    build_context_block,
    build_rag_prompt,
)

# Reciprocal-rank fusion constant (Cormack et al., 2009) and candidate pool sizing
RRF_K = 60
CANDIDATE_MULTIPLIER = 4
MIN_CANDIDATES = 20


class RetrievalService:
    def __init__(
        self,
        db: AsyncSession,
        embedding: EmbeddingProvider | None = None,
        llm: LLMProvider | None = None,
    ):
        self.db = db
        self.vector_store = SQLiteVectorStore(db)
        self.embedding_provider = embedding or get_embedding_provider()
        self.llm_provider = llm or get_llm_provider()

    async def search(
        self,
        query: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
        min_score: float = 0.05,
    ) -> SearchResponse:
        """Retrieves top-k source-aware chunks using hybrid vector + BM25 retrieval.

        Candidates are ranked by reciprocal-rank fusion of the two rankings. Each result's
        relevance_score is max(cosine similarity, lexical query coverage), both in [0, 1],
        so an exact keyword match is not discarded by a low embedding similarity.
        Chunks with identical text (e.g. the same PDF indexed twice) are returned once.
        """
        query_vec = await self.embedding_provider.embed_text(query)
        vector_ranked = await self.vector_store.search(
            query_vector=query_vec,
            top_k=None,
            document_ids=document_ids,
        )
        if not vector_ranked:
            return SearchResponse(query=query, results=[])

        pool = max(top_k * CANDIDATE_MULTIPLIER, MIN_CANDIDATES)
        lexical_index = await get_bm25_index(self.db)
        lexical_ranked = lexical_index.search(query, limit=pool, document_ids=document_ids)

        cosine = dict(vector_ranked)
        coverage = {cid: cov for cid, _, cov in lexical_ranked}
        fused: dict[str, float] = defaultdict(float)
        for rank, (cid, _) in enumerate(vector_ranked[:pool], 1):
            fused[cid] += 1.0 / (RRF_K + rank)
        for rank, (cid, _, _) in enumerate(lexical_ranked, 1):
            fused[cid] += 1.0 / (RRF_K + rank)

        candidates = sorted(fused, key=lambda cid: fused[cid], reverse=True)
        scores = {cid: max(cosine.get(cid, 0.0), coverage.get(cid, 0.0)) for cid in candidates}
        candidates = [cid for cid in candidates if scores[cid] >= min_score]
        if not candidates:
            return SearchResponse(query=query, results=[])

        # Load chunks with related Document and Page
        stmt = (
            select(Chunk)
            .where(Chunk.id.in_(candidates))
            .options(selectinload(Chunk.document), selectinload(Chunk.page))
        )
        res = await self.db.execute(stmt)
        chunk_lookup = {c.id: c for c in res.scalars().all()}

        sources: list[SourceReference] = []
        seen_texts: set[str] = set()
        for cid in candidates:
            chunk = chunk_lookup.get(cid)
            if not chunk:
                continue
            text_key = " ".join(chunk.text.split()).lower()
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)

            doc_title = chunk.document.title or chunk.document.filename if chunk.document else "Untitled Document"
            page_num = chunk.page.page_number if chunk.page else 1

            sources.append(
                SourceReference(
                    document_id=chunk.document_id,
                    document_title=doc_title,
                    page_number=page_num,
                    chunk_id=chunk.id,
                    relevance_score=round(scores[cid], 4),
                    section=chunk.section,
                    excerpt=chunk.text,
                )
            )
            if len(sources) == top_k:
                break

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
        gen_result = await self.llm_provider.generate(prompt, system_prompt=GROUNDING_SYSTEM_PROMPT)

        if "Insufficient evidence" in gen_result.text:
            has_sufficient = False

        return ChatResponse(
            question=question,
            answer=gen_result.text,
            sources=sources if has_sufficient else [],
            has_sufficient_evidence=has_sufficient,
            prompt_tokens=gen_result.prompt_tokens,
            completion_tokens=gen_result.completion_tokens,
        )
