import io
import pytest
from httpx import AsyncClient
from pypdf import PageObject, PdfWriter


def make_pdf(title: str, text: str) -> bytes:
    writer = PdfWriter()
    page = PageObject.create_blank_page(width=612, height=792)
    writer.add_page(page)
    writer.add_metadata({"/Title": title, "/Author": "Test Author"})
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.mark.asyncio
async def test_comparison_validation(client: AsyncClient):
    # Less than 2 documents rejected
    res = await client.post("/api/research/compare", json={"document_ids": ["single-id"]})
    assert res.status_code == 422 or res.status_code == 400


@pytest.mark.asyncio
async def test_comparison_lifecycle(client: AsyncClient):
    # Upload Paper 1
    pdf1 = make_pdf("Quantized NPU Transformers", "Methodology: We implement INT4 quantization for NPU latency.")
    res1 = await client.post(
        "/api/documents",
        files={"file": ("npu_paper.pdf", pdf1, "application/pdf")},
        data={"title": "Quantized NPU Transformers"},
    )
    doc1_id = res1.json()["id"]

    # Upload Paper 2
    pdf2 = make_pdf("Verification in Scholarly RAG", "Methodology: We design a citation verification pipeline for RAG.")
    res2 = await client.post(
        "/api/documents",
        files={"file": ("rag_paper.pdf", pdf2, "application/pdf")},
        data={"title": "Verification in Scholarly RAG"},
    )
    doc2_id = res2.json()["id"]

    # Run default comparison
    compare_payload = {
        "document_ids": [doc1_id, doc2_id],
    }
    comp_res = await client.post("/api/research/compare", json=compare_payload)
    assert comp_res.status_code == 200
    data = comp_res.json()

    assert "dimensions" in data
    assert len(data["dimensions"]) >= 4
    assert len(data["comparisons"]) == 2
    assert data["comparisons"][0]["document_id"] == doc1_id
    assert data["comparisons"][1]["document_id"] == doc2_id
    assert "synthesis" in data
    assert "Quantized NPU Transformers" in data["synthesis"]

    # Run custom dimensions comparison
    custom_payload = {
        "document_ids": [doc1_id, doc2_id],
        "dimensions": ["Methodology", "Performance Gains"],
    }
    custom_res = await client.post("/api/research/compare", json=custom_payload)
    assert custom_res.status_code == 200
    custom_data = custom_res.json()
    assert custom_data["dimensions"] == ["Methodology", "Performance Gains"]
    assert "Methodology" in custom_data["comparisons"][0]["dimension_values"]
