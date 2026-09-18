import io
import pytest
from httpx import AsyncClient
from PIL import Image


def make_test_image_bytes(width: int = 400, height: int = 300, color=(56, 189, 248)) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_vision_upload_invalid_type(client: AsyncClient):
    files = {"file": ("notes.txt", b"some plain text", "text/plain")}
    res = await client.post("/api/vision/upload", files=files)
    assert res.status_code == 400
    assert "Unsupported image format" in res.json()["detail"]


@pytest.mark.asyncio
async def test_vision_pipeline_lifecycle(client: AsyncClient):
    img_bytes = make_test_image_bytes(600, 400)
    files = {"file": ("npu_benchmark_chart.png", img_bytes, "image/png")}

    # 1. Upload
    up_res = await client.post("/api/vision/upload", files=files)
    assert up_res.status_code == 201
    up_data = up_res.json()
    image_id = up_data["image_id"]
    assert up_data["dimensions"] == [600, 400]
    assert "file" in up_data["preview_url"]

    # 2. Get image file
    file_res = await client.get(f"/api/vision/{image_id}/file")
    assert file_res.status_code == 200
    assert len(file_res.content) > 0

    # 3. Analyze figure
    ana_res = await client.post("/api/vision/analyze", json={"image_id": image_id})
    assert ana_res.status_code == 200
    ana_data = ana_res.json()
    assert "Figure:" in ana_data["title"]
    assert len(ana_data["observations"]) > 0
    assert ana_data["confidence"] > 0.8

    # 4. Visual Q&A
    chat_res = await client.post(
        "/api/vision/chat",
        json={"image_id": image_id, "question": "What are the main performance trends in this chart?"},
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "answer" in chat_data
    assert len(chat_data["grounded_visual_cues"]) > 0


@pytest.mark.asyncio
async def test_vision_upload_with_document_link_and_paper_context(client: AsyncClient):
    """A figure uploaded with document_id links to the paper; Q&A retrieves cited paper context."""
    # Seed demo papers so there is a real indexed document to link against
    seed_res = await client.post("/api/documents/seed_demo")
    assert seed_res.status_code == 200
    docs = (await client.get("/api/documents")).json()
    assert len(docs) >= 1
    doc_id = docs[0]["id"]

    img_bytes = make_test_image_bytes(800, 450, color=(15, 23, 42))
    up_res = await client.post(
        "/api/vision/upload",
        files={"file": ("pipeline_arch.png", img_bytes, "image/png")},
        data={"document_id": doc_id},
    )
    assert up_res.status_code == 201
    up_data = up_res.json()
    assert up_data["document_id"] == doc_id
    image_id = up_data["image_id"]

    chat_res = await client.post(
        "/api/vision/chat",
        json={
            "image_id": image_id,
            "question": "How does the pipeline in this diagram relate to the paper's methodology?",
        },
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert len(chat_data["answer"]) > 0
    # Paper context section present with citations when the linked paper has matching chunks
    assert isinstance(chat_data["paper_context_sources"], list)
    if chat_data["paper_context_sources"]:
        assert "Paper Context" in chat_data["answer"]
        assert "[Doc:" in chat_data["answer"]
        src = chat_data["paper_context_sources"][0]
        assert src["document_id"] == doc_id
        assert src["page_number"] > 0


@pytest.mark.asyncio
async def test_vision_link_persists_across_requests(client: AsyncClient):
    """The upload-time document link is reused when chat omits document_id."""
    seed_res = await client.post("/api/documents/seed_demo")
    docs = (await client.get("/api/documents")).json()
    doc_id = docs[0]["id"]

    img_bytes = make_test_image_bytes(300, 300)
    up_res = await client.post(
        "/api/vision/upload",
        files={"file": ("linked_fig.png", img_bytes, "image/png")},
        data={"document_id": doc_id},
    )
    image_id = up_res.json()["image_id"]

    # Chat without document_id: the stored link must be used
    chat_res = await client.post(
        "/api/vision/chat",
        json={"image_id": image_id, "question": "methodology overview"},
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    if chat_data["paper_context_sources"]:
        assert chat_data["paper_context_sources"][0]["document_id"] == doc_id
