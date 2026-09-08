import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Chunk, Document, Page
from app.providers.vector_store import SQLiteVectorStore, cosine_similarity


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v2) == pytest.approx(1.0)

    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v3) == pytest.approx(0.0)

    v4 = [1.0, 1.0, 0.0]
    assert cosine_similarity(v1, v4) == pytest.approx(0.7071, abs=1e-3)


@pytest.mark.asyncio
async def test_vector_store_lifecycle(db_session: AsyncSession):
    # Setup document, page, chunks
    doc1 = Document(filename="doc1.pdf", content_hash="hash1", file_path="/tmp/1", status="INDEXED")
    doc2 = Document(filename="doc2.pdf", content_hash="hash2", file_path="/tmp/2", status="INDEXED")
    db_session.add_all([doc1, doc2])
    await db_session.flush()

    p1 = Page(document_id=doc1.id, page_number=1, text="Page 1")
    p2 = Page(document_id=doc2.id, page_number=1, text="Page 2")
    db_session.add_all([p1, p2])
    await db_session.flush()

    c1 = Chunk(document_id=doc1.id, page_id=p1.id, chunk_index=0, text="Deep learning on NPU")
    c2 = Chunk(document_id=doc2.id, page_id=p2.id, chunk_index=0, text="Historical archaeology study")
    db_session.add_all([c1, c2])
    await db_session.flush()

    store = SQLiteVectorStore(db_session)

    # Add vectors
    v1 = [1.0, 0.5, 0.0]
    v2 = [0.0, 0.1, 0.9]
    await store.add_vectors([(c1.id, doc1.id, v1), (c2.id, doc2.id, v2)])

    # Search with query close to v1
    query_vec = [0.9, 0.4, 0.0]
    results = await store.search(query_vec, top_k=2)
    assert len(results) == 2
    # c1 should have highest similarity
    assert results[0][0] == c1.id
    assert results[0][1] > 0.9

    # Search with document filter
    filtered = await store.search(query_vec, top_k=2, document_ids=[doc2.id])
    assert len(filtered) == 1
    assert filtered[0][0] == c2.id

    # Delete doc1 vectors
    await store.delete_by_document(doc1.id)
    after_del = await store.search(query_vec, top_k=2)
    assert len(after_del) == 1
    assert after_del[0][0] == c2.id
