"""Keeps stored vectors and the configured embedding provider in agreement.

Different providers can share a dimension (the hash and MiniLM providers are both 384-d),
so searching an index built by one provider with query vectors from another would silently
return unrelated chunks. The index records its provider and refuses mismatched use.
"""

import json

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Chunk, ChunkEmbedding, IndexSetting
from app.providers.base import EmbeddingProvider

PROVIDER_KEY = "embedding_provider"
# Indexes created before the provider was recorded could only have used the development provider
LEGACY_PROVIDER = "development-feature-hash-384"


async def get_index_provider(db: AsyncSession) -> str | None:
    setting = await db.get(IndexSetting, PROVIDER_KEY)
    if setting:
        return setting.value
    has_vectors = await db.scalar(select(ChunkEmbedding.id).limit(1))
    return LEGACY_PROVIDER if has_vectors else None


async def ensure_index_matches(db: AsyncSession, provider: EmbeddingProvider) -> None:
    indexed_with = await get_index_provider(db)
    if indexed_with is not None and indexed_with != provider.name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"The document index was built with '{indexed_with}' but the configured embedding "
                f"provider is '{provider.name}'. Run: python scripts/reindex_embeddings.py"
            ),
        )


async def record_index_provider(db: AsyncSession, provider: EmbeddingProvider) -> None:
    await db.merge(IndexSetting(key=PROVIDER_KEY, value=provider.name))


async def reembed_all_chunks(db: AsyncSession, provider: EmbeddingProvider, batch_size: int = 256) -> int:
    """Replaces every stored vector with one from `provider`, reusing the existing chunks."""
    rows = (
        await db.execute(select(Chunk.id, Chunk.document_id, Chunk.text).order_by(Chunk.document_id, Chunk.chunk_index))
    ).all()
    await db.execute(delete(ChunkEmbedding))
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        vectors = await provider.embed_batch([r.text for r in batch])
        db.add_all(
            ChunkEmbedding(chunk_id=r.id, document_id=r.document_id, embedding_json=json.dumps(v))
            for r, v in zip(batch, vectors, strict=True)
        )
    await record_index_provider(db, provider)
    await db.commit()
    return len(rows)
