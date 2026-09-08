import io
import pytest
from httpx import AsyncClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def make_learning_pdf(title: str, text: str) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setTitle(title)
    c.setAuthor("Prof. Smith")
    c.drawString(72, 700, f"Title: {title}")
    c.drawString(72, 670, text)
    c.drawString(72, 640, "Key findings indicate that on-device execution guarantees privacy and predictable latency.")
    c.showPage()
    c.save()
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_learning_endpoints(client: AsyncClient):
    # Upload test document
    pdf = make_learning_pdf("Neural Network Quantization", "Methodology: INT4 weights reduce latency significantly on hardware.")
    upload_res = await client.post(
        "/api/documents",
        files={"file": ("nn_quant.pdf", pdf, "application/pdf")},
        data={"title": "Neural Network Quantization"},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 1. Concept Explainer (Beginner)
    explain_req = {
        "concept": "Neural Network Quantization",
        "document_ids": [doc_id],
        "level": "beginner",
    }
    exp_res = await client.post("/api/learning/explain", json=explain_req)
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert exp_data["concept"] == "Neural Network Quantization"
    assert exp_data["level"] == "beginner"
    assert len(exp_data["explanation"]) > 0
    assert len(exp_data["key_takeaways"]) > 0

    # 2. Concept Explainer (Deep Dive)
    deep_req = {
        "concept": "Neural Network Quantization",
        "document_ids": [doc_id],
        "level": "deep_dive",
    }
    deep_res = await client.post("/api/learning/explain", json=deep_req)
    assert deep_res.status_code == 200
    assert "Architectural Analysis" in deep_res.json()["explanation"]

    # 3. Quiz Generator
    quiz_req = {
        "document_ids": [doc_id],
        "question_count": 2,
        "difficulty": "medium",
    }
    quiz_res = await client.post("/api/learning/quiz", json=quiz_req)
    assert quiz_res.status_code == 200
    quiz_data = quiz_res.json()
    assert "questions" in quiz_data
    assert len(quiz_data["questions"]) > 0

    q = quiz_data["questions"][0]
    assert len(q["options"]) == 4
    assert 0 <= q["correct_answer_index"] < 4
    assert len(q["explanation"]) > 0
    assert q["source"] is not None

    # 4. Flashcards Generator
    fc_res = await client.post("/api/learning/flashcards")
    assert fc_res.status_code == 200
    fc_data = fc_res.json()
    assert "flashcards" in fc_data
    assert len(fc_data["flashcards"]) > 0
    assert "front_prompt" in fc_data["flashcards"][0]
    assert "back_answer" in fc_data["flashcards"][0]
