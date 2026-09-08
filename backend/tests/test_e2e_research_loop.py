"""End-to-end integration and smoke test verifying the complete research-to-learning loop."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_complete_e2e_research_and_learning_loop(client: AsyncClient):
    # 1. Health check telemetry
    health_res = await client.get("/api/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "healthy"
    assert health_data["provider_backend"] in ("development", "qualcomm")
    assert health_data["external_providers_enabled"] is False

    # 2. One-click Medical-AI demo seeding
    seed_res = await client.post("/api/documents/seed_demo")
    assert seed_res.status_code == 200
    seed_data = seed_res.json()
    assert seed_data["documents_seeded"] >= 3
    assert seed_data["figures_seeded"] >= 1

    # 3. List documents
    docs_res = await client.get("/api/documents")
    assert docs_res.status_code == 200
    docs = docs_res.json()
    assert len(docs) >= 3
    doc_ids = [d["id"] for d in docs]
    titles = [d["title"] for d in docs]
    assert any("Radiology" in t or "Multimodal" in t for t in titles)

    # 4. Direct Retrieval Query (Pneumonia AUC from Paper 1)
    chat_req_direct = {
        "question": "What diagnostic accuracy and AUC did the multimodal model achieve for pneumonia detection?",
        "top_k": 3,
    }
    chat_res_1 = await client.post("/api/chat", json=chat_req_direct)
    assert chat_res_1.status_code == 200
    res_1_data = chat_res_1.json()
    assert res_1_data["has_sufficient_evidence"] is True
    assert len(res_1_data["sources"]) > 0
    assert any("91.4%" in s["excerpt"] or "AUC" in s["excerpt"] for s in res_1_data["sources"])
    assert "Page" in res_1_data["answer"]
    assert "Clinical Multimodal Transformers" in res_1_data["answer"]

    # 5. Direct Retrieval Query (Clinical Privacy from Paper 2)
    chat_req_privacy = {
        "question": "Why is on-device inference critical for clinical language models handling electronic health records?",
        "top_k": 3,
    }
    chat_res_2 = await client.post("/api/chat", json=chat_req_privacy)
    assert chat_res_2.status_code == 200
    res_2_data = chat_res_2.json()
    assert res_2_data["has_sufficient_evidence"] is True
    assert len(res_2_data["sources"]) > 0

    # 6. Refusal / Insufficient Evidence Query
    chat_req_refusal = {
        "question": "What is the surgical resection margin for stage IV glioblastoma multiforme recurrence?",
        "top_k": 3,
    }
    chat_res_3 = await client.post("/api/chat", json=chat_req_refusal)
    assert chat_res_3.status_code == 200
    res_3_data = chat_res_3.json()
    # Expect either refusal flag or explicit insufficient evidence notice
    assert ("Insufficient evidence" in res_3_data["answer"]) or (not res_3_data["has_sufficient_evidence"])

    # 7. Cross-Paper Comparison Matrix
    compare_req = {
        "document_ids": doc_ids[:2],
        "dimensions": ["Methodology & Architecture", "Key Findings & Metrics"],
    }
    compare_res = await client.post("/api/research/compare", json=compare_req)
    assert compare_res.status_code == 200
    comp_data = compare_res.json()
    assert len(comp_data["comparisons"]) == 2
    assert "Methodology & Architecture" in comp_data["comparisons"][0]["dimension_values"]
    assert len(comp_data["all_sources"]) > 0

    # 8. Learning Concept Explainer
    explain_req = {
        "concept": "Multimodal Transformers",
        "document_ids": [doc_ids[0]],
        "level": "intermediate",
    }
    exp_res = await client.post("/api/learning/explain", json=explain_req)
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert len(exp_data["explanation"]) > 0
    assert len(exp_data["key_takeaways"]) > 0

    # 9. Formative Quiz Generation
    quiz_req = {
        "document_ids": doc_ids[:2],
        "question_count": 2,
        "difficulty": "medium",
    }
    quiz_res = await client.post("/api/learning/quiz", json=quiz_req)
    assert quiz_res.status_code == 200
    q_data = quiz_res.json()
    assert len(q_data["questions"]) > 0
    assert q_data["questions"][0]["source"] is not None

    # 10. Active Recall Flashcards
    fc_res = await client.post("/api/learning/flashcards")
    assert fc_res.status_code == 200
    fc_data = fc_res.json()
    assert len(fc_data["flashcards"]) > 0
    assert fc_data["flashcards"][0]["source_hint"] is not None

    # 11. Multimodal Figure Upload and Analysis
    fig_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02\x00\x00\x00\x02\x08\x02\x00\x00\x00\xfd\xd4\x9as\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
    up_fig_res = await client.post(
        "/api/vision/upload",
        files={"file": ("roc_curve.png", fig_bytes, "image/png")},
    )
    assert up_fig_res.status_code == 201
    img_data = up_fig_res.json()
    img_id = img_data["image_id"]

    analyze_res = await client.post("/api/vision/analyze", json={"image_id": img_id})
    assert analyze_res.status_code == 200
    assert "observations" in analyze_res.json()

    chat_fig_res = await client.post(
        "/api/vision/chat",
        json={"image_id": img_id, "question": "What is the primary trend in this chart?"},
    )
    assert chat_fig_res.status_code == 200
    assert len(chat_fig_res.json()["answer"]) > 0

    # 12. Retry document endpoint validation
    # Retry on an indexed document succeeds
    retry_res = await client.post(f"/api/documents/{doc_ids[0]}/retry")
    assert retry_res.status_code == 200
    assert retry_res.json()["status"] == "INDEXED"
