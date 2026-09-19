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
    # Rule-based analysis has no model, so it must not report a confidence score.
    assert ana_data["confidence"] is None
    assert ana_data["provider"] == "development-vision-heuristic"
    assert "600 x 400 px" in ana_data["observations"][0]

    # 4. Visual Q&A
    chat_res = await client.post(
        "/api/vision/chat",
        json={"image_id": image_id, "question": "What are the main performance trends in this chart?"},
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "answer" in chat_data
    assert len(chat_data["grounded_visual_cues"]) > 0
    # A trend question cannot be answered from pixel statistics; say so, don't invent one.
    assert "does not read" in chat_data["answer"]


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


def _bar_chart_png() -> bytes:
    from PIL import ImageDraw

    img = Image.new("RGB", (640, 420), "white")
    draw = ImageDraw.Draw(img)
    draw.line([60, 370, 600, 370], fill="black", width=2)
    draw.line([60, 40, 60, 370], fill="black", width=2)
    for i, h in enumerate([220, 150, 300, 90]):
        x = 110 + i * 120
        draw.rectangle([x, 370 - h, x + 70, 370], fill=(59, 130, 246))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_vision_category_comes_from_pixels_not_filename(client: AsyncClient):
    """The same image must get the same category whatever it is called."""
    png = _bar_chart_png()
    types = []
    for name in ("figure1.png", "system_architecture_diagram.png", "latency_benchmark_chart.png"):
        up = await client.post("/api/vision/upload", files={"file": (name, png, "image/png")})
        ana = await client.post("/api/vision/analyze", json={"image_id": up.json()["image_id"]})
        types.append(ana.json()["figure_type"])

    assert len(set(types)) == 1
    assert types[0].startswith("Line-art figure")


@pytest.mark.asyncio
async def test_vision_upload_rejects_truncated_image(client: AsyncClient):
    """A file that cannot be decoded is refused at upload, not analysed with made-up values."""
    truncated = make_test_image_bytes(200, 200)[:-40]
    res = await client.post("/api/vision/upload", files={"file": ("cut.png", truncated, "image/png")})
    assert res.status_code == 400
