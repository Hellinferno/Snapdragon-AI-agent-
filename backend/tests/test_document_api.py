import io
import pytest
from httpx import AsyncClient
from pypdf import PageObject, PdfWriter


def generate_pdf_bytes(title: str = "Test Doc") -> bytes:
    """Helper to generate a small in-memory PDF."""
    writer = PdfWriter()
    page1 = PageObject.create_blank_page(width=612, height=792)
    page2 = PageObject.create_blank_page(width=612, height=792)
    writer.add_page(page1)
    writer.add_page(page2)
    writer.add_metadata({"/Title": title, "/Author": "Lead Author"})

    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ScholarEdge"


@pytest.mark.asyncio
async def test_upload_non_pdf_rejected(client: AsyncClient):
    files = {"file": ("test.txt", b"Hello world text file", "text/plain")}
    response = await client.post("/api/documents", files=files)
    assert response.status_code == 400
    assert "Only PDF documents are supported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_and_lifecycle(client: AsyncClient):
    pdf_bytes = generate_pdf_bytes("Neural Computation Study")
    files = {"file": ("neural_computation.pdf", pdf_bytes, "application/pdf")}
    data = {"title": "Neural Computation Study", "authors": "Lead Author"}

    # 1. Upload
    response = await client.post("/api/documents", files=files, data=data)
    assert response.status_code == 201
    upload_res = response.json()
    doc_id = upload_res["id"]
    assert upload_res["status"] == "INDEXED"
    assert upload_res["filename"] == "neural_computation.pdf"

    # 2. Duplicate upload returns existing record
    dup_res = await client.post("/api/documents", files=files)
    assert dup_res.status_code == 201
    assert dup_res.json()["id"] == doc_id
    assert "already uploaded" in dup_res.json()["message"]

    # 3. List documents
    list_res = await client.get("/api/documents")
    assert list_res.status_code == 200
    docs = list_res.json()
    assert len(docs) == 1
    assert docs[0]["id"] == doc_id
    assert docs[0]["page_count"] == 2
    assert docs[0]["status"] == "INDEXED"

    # 4. Get document detail
    detail_res = await client.get(f"/api/documents/{doc_id}")
    assert detail_res.status_code == 200
    doc_detail = detail_res.json()
    assert doc_detail["id"] == doc_id
    assert len(doc_detail["pages"]) == 2
    assert doc_detail["pages"][0]["page_number"] == 1
    assert doc_detail["pages"][1]["page_number"] == 2

    # 5. Delete document
    del_res = await client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200

    # 6. Verify 404 after deletion
    not_found = await client.get(f"/api/documents/{doc_id}")
    assert not_found.status_code == 404

    # 7. Verify list is empty
    empty_list = await client.get("/api/documents")
    assert len(empty_list.json()) == 0


@pytest.mark.asyncio
async def test_seed_demo_endpoint(client: AsyncClient):
    response = await client.post("/api/documents/seed_demo")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["documents_seeded"] >= 1
    assert data["figures_seeded"] >= 1

    # Verify documents are returned in list
    list_res = await client.get("/api/documents")
    assert list_res.status_code == 200
    docs = list_res.json()
    assert len(docs) >= 1

