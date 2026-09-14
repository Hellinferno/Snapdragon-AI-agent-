import json

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Chunk, ChunkEmbedding, Document, Page
from app.providers.base import EmbeddingProvider
from app.providers.embedding_provider import DevelopmentEmbeddingProvider
from app.services.embedding_index import (
    LEGACY_PROVIDER,
    ensure_index_matches,
    get_index_provider,
    reembed_all_chunks,
)
from app.services.retrieval_service import RetrievalService


class ConstantProvider(EmbeddingProvider):
    name = "constant-384"
    dimension = 384

    async def embed_text(self, text):
        return [1.0] + [0.0] * 383

    async def embed_batch(self, texts):
        return [await self.embed_text(t) for t in texts]


async def _index_one_chunk(db: AsyncSession) -> Chunk:
    doc = Document(filename="a.pdf", title="A", content_hash="h", file_path="/tmp/a.pdf", status="INDEXED")
    db.add(doc)
    await db.flush()
    page = Page(document_id=doc.id, page_number=1, text="t")
    db.add(page)
    await db.flush()
    chunk = Chunk(document_id=doc.id, page_id=page.id, chunk_index=0, text="overfitting and generalization")
    db.add(chunk)
    await db.flush()
    vec = await DevelopmentEmbeddingProvider().embed_text(chunk.text)
    db.add(ChunkEmbedding(chunk_id=chunk.id, document_id=doc.id, embedding_json=json.dumps(vec)))
    await db.commit()
    return chunk


@pytest.mark.asyncio
async def test_empty_index_accepts_any_provider(db_session: AsyncSession):
    assert await get_index_provider(db_session) is None
    await ensure_index_matches(db_session, ConstantProvider())


@pytest.mark.asyncio
async def test_unrecorded_index_is_treated_as_legacy_development_vectors(db_session: AsyncSession):
    await _index_one_chunk(db_session)
    assert await get_index_provider(db_session) == LEGACY_PROVIDER
    await ensure_index_matches(db_session, DevelopmentEmbeddingProvider())


@pytest.mark.asyncio
async def test_search_with_mismatched_provider_is_refused(db_session: AsyncSession):
    await _index_one_chunk(db_session)
    with pytest.raises(HTTPException) as err:
        await RetrievalService(db_session, embedding=ConstantProvider()).search("overfitting")
    assert err.value.status_code == 409
    assert "reindex_embeddings.py" in err.value.detail


@pytest.mark.asyncio
async def test_reembed_replaces_vectors_and_records_provider(db_session: AsyncSession):
    chunk = await _index_one_chunk(db_session)
    assert await reembed_all_chunks(db_session, ConstantProvider()) == 1
    assert await get_index_provider(db_session) == "constant-384"
    stored = (await db_session.execute(select(ChunkEmbedding))).scalars().all()
    assert [e.chunk_id for e in stored] == [chunk.id]
    assert json.loads(stored[0].embedding_json)[:2] == [1.0, 0.0]
    results = await RetrievalService(db_session, embedding=ConstantProvider()).search("overfitting", min_score=0.0)
    assert results.results[0].chunk_id == chunk.id
