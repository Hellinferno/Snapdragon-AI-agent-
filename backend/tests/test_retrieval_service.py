import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Chunk, Document, Page
from app.providers.embedding_provider import embedding_provider
from app.providers.factory import get_embedding_provider, get_llm_provider
from app.providers.vector_store import SQLiteVectorStore
from app.services.retrieval_service import RetrievalService


@pytest.mark.asyncio
async def test_retrieval_service_search_and_chat(db_session: AsyncSession):
    # Setup indexed document
    doc = Document(
        filename="npu_benchmark.pdf",
        title="NPU Architecture Evaluation",
        content_hash="benchmarkhash123",
        file_path="/tmp/npu.pdf",
        status="INDEXED",
    )
    db_session.add(doc)
    await db_session.flush()

    page = Page(document_id=doc.id, page_number=2, text="Methodology text")
    db_session.add(page)
    await db_session.flush()

    chunk = Chunk(
        document_id=doc.id,
        page_id=page.id,
        chunk_index=0,
        text="On-device quantized transformer inference yields a 4.2x latency improvement.",
        section="Methodology",
    )
    db_session.add(chunk)
    await db_session.flush()

    # Index embedding using development provider (test default)
    vec = await embedding_provider.embed_text(chunk.text)
    store = SQLiteVectorStore(db_session)
    await store.add_vectors([(chunk.id, doc.id, vec)])

    # Use development providers for test to match indexed embeddings
    dev_embedding = embedding_provider
    dev_llm = get_llm_provider("development")
    service = RetrievalService(db_session, embedding=dev_embedding, llm=dev_llm)

    # 1. Search with matching query
    search_res = await service.search("quantized transformer latency", top_k=3)
    assert len(search_res.results) > 0
    top_hit = search_res.results[0]
    assert top_hit.chunk_id == chunk.id
    assert top_hit.page_number == 2
    assert top_hit.section == "Methodology"
    assert top_hit.document_title == "NPU Architecture Evaluation"

    # 2. Chat with matching query
    chat_res = await service.chat("What is the latency improvement for quantized transformer?")
    assert chat_res.has_sufficient_evidence is True
    assert len(chat_res.sources) > 0
    assert "NPU Architecture Evaluation" in chat_res.answer or "latency" in chat_res.answer

    # 3. Chat with completely unrelated query
    unrelated_res = await service.chat("What is the recipe for baking chocolate brownies?")
    assert unrelated_res.has_sufficient_evidence is False
    assert "Insufficient evidence" in unrelated_res.answer
