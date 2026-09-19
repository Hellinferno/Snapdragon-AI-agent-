"""Verification tests for P0/P1/P2 capabilities:
- Actual Qualcomm ONNX model execution
- Truth in runtime telemetry (no false NPU claims)
- Evidence-based comparison (cited cells, explicit gaps)
- 4-tier quiz generation with explicit correct_answer and explanation
- Demonstrable privacy telemetry
"""

import pytest
from httpx import AsyncClient
import numpy as np

from app.providers.qualcomm.qualcomm_providers import (
    QualcommEmbeddingProvider,
    QualcommLLMProvider,
    QualcommVisionProvider,
)
from app.providers.qualcomm.qualcomm_config import QualcommConfig, onnx_artifact_exists


@pytest.mark.asyncio
async def test_qualcomm_onnx_embedding_execution():
    provider = QualcommEmbeddingProvider()
    assert provider.telemetry["runtime_engine"] == "ONNX Runtime"
    # Dev machine is Intel ThinkBook, so hardware NPU must be False
    assert provider.telemetry["hardware_npu_active"] is False
    # Model artifacts are gitignored, so CI runs without them in fallback mode
    assert provider.telemetry["runtime_status"] in (
        "Development Host (CPU Simulation)",
        "Fallback Mode (Model Not Found)",
        "Fallback Mode (Session Load Failed)",
    )

    # If ONNX session failed to load (IR version mismatch), skip
    if provider._session is None:
        pytest.skip("ONNX model not available (IR version mismatch)")

    vec = await provider.embed_text("Deep neural embeddings on Snapdragon PC")
    assert len(vec) == 384
    # Check L2 unit normalization
    norm = np.linalg.norm(np.array(vec))
    assert abs(norm - 1.0) < 1e-3
    assert provider.telemetry["cold_latency_ms"] > 0


@pytest.mark.asyncio
async def test_qualcomm_qairt_llm_telemetry():
    provider = QualcommLLMProvider()
    assert provider.telemetry["runtime_engine"] == "GenAI Inference Extensions (QAIRT)"
    assert provider.telemetry["hardware_npu_active"] is False
    status = provider.telemetry["runtime_status"]
    assert "Hardware Validation Pending" in status or status == "Fallback Mode (Model Not Found)" or "QAIRT Bundle Detected" in status

    # If tokenizer or session not available, skip generation test
    if provider._session is None or provider._tokenizer is None:
        pytest.skip("QAIRT bundle not at expected path or ONNX session failed")

    prompt = (
        "### CONTEXT:\n"
        "[Source 1: \"Clinical Multimodal AI\", Page 5, Section: \"Results\"]\n"
        "The model achieved 91.4% AUC on pneumonia chest radiography.\n"
        "### QUESTION:\n"
        "What AUC did the model achieve on radiography?"
    )
    result = await provider.generate(prompt)
    # Hardware validation pending on physical Snapdragon NPU; only verify
    # execution completes and returns tokens, not output quality
    # Verify execution succeeds and returns tokens
    assert isinstance(result.text, str)
    assert len(result.text) > 0
    assert result.completion_tokens > 0
    assert provider.telemetry["tokens_per_second"] > 0


@pytest.mark.asyncio
async def test_qualcomm_onnx_vision_classification():
    from PIL import Image
    import io

    # backend/models/ is gitignored, so CI has no MobileNet artifact; the absent
    # artifact is a skip, not a failure.
    if not onnx_artifact_exists(QualcommConfig().vision_model_id):
        pytest.skip(
            "MobileNet-v2 ONNX artifact absent on this host "
            "(run scripts/download_qualcomm_models.py to exercise the vision path)"
        )

    try:
        provider = QualcommVisionProvider()
    except RuntimeError as e:
        if "Unsupported model IR version" in str(e):
            pytest.skip("ONNX model not available (IR version mismatch)")
        raise

    assert provider.telemetry["runtime_engine"] == "ONNX Runtime"
    assert provider.telemetry["hardware_npu_active"] is False

    # If ONNX session failed to load (IR version mismatch), skip
    if provider._session is None:
        pytest.skip("ONNX model not available (IR version mismatch)")

    # Create synthetic image
    img = Image.new("RGB", (256, 256), color=(50, 100, 150))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    analysis = await provider.analyze_figure(buf.getvalue(), "fig1.png")
    assert analysis.figure_type in provider.classes
    assert len(analysis.observations) >= 3
    assert analysis.confidence > 0.0


@pytest.mark.asyncio
async def test_runtime_and_privacy_telemetry_endpoint(client: AsyncClient):
    res = await client.get("/api/runtime/status")
    assert res.status_code == 200
    data = res.json()

    # P0 #2 verification: Never call CPU simulation "NPU active"
    assert data["hardware_npu_active"] is False
    assert "Inactive" in data["npu_status"] or "Host Development" in data["npu_status"]

    # P2 Privacy Mode verification
    checklist = {item["item"]: item["status"] for item in data["privacy_checklist"]}
    assert checklist["Documents stored locally"] is True
    assert checklist["Embeddings stored locally"] is True
    assert checklist["Vector search local"] is True
    assert checklist["AI inference local"] is True
    assert checklist["No document upload"] is True
    # External providers setting depends on ALLOW_EXTERNAL_PROVIDERS env var
    # assert checklist["External providers disabled"] is True


@pytest.mark.asyncio
async def test_compare_studio_is_evidence_based(client: AsyncClient):
    """Every comparison cell quotes a cited passage or is reported as a gap;
    nothing ranks papers as "stronger" and no cross-paper claim is invented."""
    await client.post("/api/documents/seed_demo")
    docs = {d["title"]: d["id"] for d in (await client.get("/api/documents")).json()}
    radiology = docs["Clinical Multimodal Transformers for Diagnostic Radiology"]
    privacy = docs["Privacy-Preserving On-Device Clinical Language Models"]

    res = await client.post(
        "/api/research/compare",
        json={"document_ids": [radiology, privacy], "criteria": ["pneumonia detection AUC"]},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["method"] == "extractive"
    assert "recommendations" not in data and "commonalities" not in data
    assert "Stronger" not in data["synthesis"]

    for item in data["comparisons"]:
        assert set(item["cells"]) == set(data["dimensions"])
        for dim, cell in item["cells"].items():
            if cell["reported"]:
                src = cell["source"]
                assert src["document_id"] == item["document_id"]
                # The statement is verbatim text of the cited passage.
                assert cell["statement"].rstrip("…") in " ".join(src["excerpt"].split())
            else:
                assert cell["source"] is None
                assert any(
                    g["document_id"] == item["document_id"] and g["dimension"] == dim
                    for g in data["evidence_gaps"]
                )

    # The radiology paper's result is found where the paper states it (page 4).
    radiology_cells = next(c for c in data["comparisons"] if c["document_id"] == radiology)["cells"]
    assert radiology_cells["Results"]["reported"]
    assert "91.4% AUC" in radiology_cells["Results"]["statement"]
    assert radiology_cells["Results"]["source"]["page_number"] == 4

    [match] = data["criterion_matches"]
    assert match["criterion"] == "pneumonia detection AUC"
    assert {e["document_id"] for e in match["evidence"]} == {radiology, privacy}
    assert match["better_match_document_id"] in (radiology, None)


@pytest.mark.asyncio
async def test_four_tier_quiz_generation(client: AsyncClient):
    # Seed demo documents first
    await client.post("/api/documents/seed_demo")

    for diff in ["easy", "medium", "hard", "research_level"]:
        res = await client.post(
            "/api/learning/quiz",
            json={"question_count": 2, "difficulty": diff},
        )
        assert res.status_code == 200
        quiz = res.json()
        assert quiz["difficulty"] == diff
        assert len(quiz["questions"]) >= 1
        for q in quiz["questions"]:
            assert "question" in q
            assert len(q["options"]) == 4
            assert 0 <= q["correct_answer_index"] < 4
            assert len(q["correct_answer"]) > 0
            assert len(q["explanation"]) > 0
            assert q["source"] is not None
            assert q["source"]["page_number"] > 0
