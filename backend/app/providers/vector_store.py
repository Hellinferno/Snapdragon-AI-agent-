import json
import math
from abc import ABC, abstractmethod
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import ChunkEmbedding


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0

    dot = 0.0
    norm1 = 0.0
    norm2 = 0.0
    for a, b in zip(v1, v2, strict=False):
        dot += a * b
        norm1 += a * a
        norm2 += b * b

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return dot / (math.sqrt(norm1) * math.sqrt(norm2))


class VectorStore(ABC):
    """Abstract interface for local vector storage and retrieval."""

    @abstractmethod
    async def add_vectors(self, entries: list[tuple[str, str, list[float]]]) -> None:
        """Stores vectors. Each entry is (chunk_id, document_id, vector)."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> list[tuple[str, float]]:
        """
        Retrieves top-k closest chunk IDs and their similarity scores.
        Returns list of (chunk_id, similarity_score).
        """
        pass

    @abstractmethod
    async def delete_by_document(self, document_id: str) -> None:
        """Purges vectors associated with a document."""
        pass


class SQLiteVectorStore(VectorStore):
    """Local, lightweight vector store persisting embeddings in SQLite."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_vectors(self, entries: list[tuple[str, str, list[float]]]) -> None:
        for chunk_id, document_id, vector in entries:
            embedding_record = ChunkEmbedding(
                chunk_id=chunk_id,
                document_id=document_id,
                embedding_json=json.dumps(vector),
            )
            self.db.add(embedding_record)
        await self.db.commit()

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> list[tuple[str, float]]:
        stmt = select(ChunkEmbedding)
        if document_ids:
            stmt = stmt.where(ChunkEmbedding.document_id.in_(document_ids))

        result = await self.db.execute(stmt)
        records = result.scalars().all()

        if not records:
            return []

        scored_results: list[tuple[str, float]] = []
        for record in records:
            chunk_vec = json.loads(record.embedding_json)
            sim = cosine_similarity(query_vector, chunk_vec)
            scored_results.append((record.chunk_id, round(sim, 4)))

        # Sort descending by similarity score
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:top_k]

    async def delete_by_document(self, document_id: str) -> None:
        await self.db.execute(
            delete(ChunkEmbedding).where(ChunkEmbedding.document_id == document_id)
        )
        await self.db.commit()
