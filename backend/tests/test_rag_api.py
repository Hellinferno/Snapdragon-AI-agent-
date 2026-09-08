import io
import pytest
from httpx import AsyncClient
from pypdf import PageObject, PdfWriter


def generate_test_pdf() -> bytes:
    writer = PdfWriter()
    page1 = PageObject.create_blank_page(width=612, height=792)
    writer.add_page(page1)
    writer.add_metadata({
        "/Title": "Snapdragon NPU Acceleration",
        "/Author": "Research Team",
    })
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.mark.asyncio
async def test_search_and_chat_endpoints(client: AsyncClient):
    # Upload test document
    pdf_bytes = generate_test_pdf()
    files = {"file": ("snapdragon_study.pdf", pdf_bytes, "application/pdf")}
    data = {"title": "Snapdragon NPU Acceleration"}

    up_res = await client.post("/api/documents", files=files, data=data)
    assert up_res.status_code == 201
    doc_id = up_res.json()["id"]

    # 1. Search endpoint
    search_payload = {"query": "Snapdragon NPU", "top_k": 5}
    search_res = await client.post("/api/search", json=search_payload)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert "results" in search_data

    # 2. Chat endpoint
    chat_payload = {
        "question": "How does Snapdragon accelerate inference?",
        "document_ids": [doc_id],
        "top_k": 3,
    }
    chat_res = await client.post("/api/chat", json=chat_payload)
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "answer" in chat_data
    assert "has_sufficient_evidence" in chat_data
    assert "sources" in chat_data
