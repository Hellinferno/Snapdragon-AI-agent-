"""Automated tests for Qualcomm AI Hub providers, factory, and benchmark harness."""

import json
import math
import pytest
from pathlib import Path

from app.providers.qualcomm.qualcomm_config import (
    QualcommConfig,
    QualcommModelUnavailable,
    onnx_artifact_exists,
)
from app.providers.qualcomm.qualcomm_providers import (
    QualcommEmbeddingProvider,
    QualcommLLMProvider,
    QualcommVisionProvider,
)
from app.providers.factory import (
    get_embedding_provider,
    get_llm_provider,
    get_vision_provider,
    get_ocr_provider,
)
from app.providers.embedding_provider import DevelopmentEmbeddingProvider
from app.providers.llm_provider import DevelopmentLLMProvider
from scripts.benchmark_snapdragon import run_full_benchmark, detect_system_telemetry


def test_qualcomm_config_and_host_detection():
    config = QualcommConfig()
    assert config.embedding_model_id == "all-MiniLM-L6-v2"
    assert config.llm_model_id == "Qwen3-4B-Instruct-2507"
    assert config.vision_model_id == "MobileNet-v2"

    env = config.detect_host_environment()
    assert "system" in env
    assert "machine" in env
    assert "detected_device" in env

    effective_providers = config.get_effective_providers()
    assert "CPUExecutionProvider" in effective_providers


@pytest.mark.asyncio
async def test_qualcomm_embedding_provider_lifecycle():
    provider = QualcommEmbeddingProvider()
    assert provider.dimension == 384
    assert "qualcomm-ai-hub" in provider.name

    # If ONNX session failed to load (IR version mismatch), use fallback
    if provider._session is None:
        pytest.skip("ONNX model not available (IR version mismatch), using fallback")

    # Single text embedding
    vec = await provider.embed_text("Snapdragon Hexagon NPU neural acceleration")
    assert len(vec) == 384
    norm = math.sqrt(sum(v * v for v in vec))
    assert abs(norm - 1.0) < 1e-3

    # Batch embedding
    batch = await provider.embed_batch(["Passage 1", "Passage 2"])
    assert len(batch) == 2
    assert len(batch[0]) == 384
    assert len(batch[1]) == 384

    assert provider.telemetry["cold_latency_ms"] > 0
    assert provider.telemetry["warm_latency_ms"] >= 0


@pytest.mark.asyncio
async def test_qualcomm_llm_provider_grounding_and_refusal():
    provider = QualcommLLMProvider()
    assert "qualcomm-ai-hub" in provider.name

    # Refusal test
    empty_res = await provider.generate("### CONTEXT:\nNO_RELEVANT_EVIDENCE\n### QUESTION:\nWhat is X?")
    assert "Insufficient evidence" in empty_res.text

    # If tokenizer not found (QAIRT bundle not at expected path), skip generation test
    if provider._session is None or provider._tokenizer is None:
        pytest.skip("QAIRT bundle not at expected path, skipping generation test")

    # QAIRT generation is intentionally unavailable until a physical Snapdragon
    # environment and the GenAI Inference Extensions runtime are integrated.
    prompt = (
        "### CONTEXT:\n"
        "[Source 1: Qualcomm Technical Whitepaper, Page 2, Section: Architecture]\n"
        "The Hexagon NPU incorporates specialized vector extensions and microcode schedulers.\n"
        "### QUESTION:\n"
        "What does the Hexagon NPU incorporate?"
    )
    grounded_res = await provider.generate(prompt)
    # Verify model executes and returns a result (not an error/refusal)
    assert isinstance(grounded_res.text, str)
    assert len(grounded_res.text) > 0
    assert grounded_res.completion_tokens > 0
    assert provider.telemetry["tokens_per_second"] > 0


@pytest.mark.asyncio
async def test_qualcomm_vision_provider(tmp_path):
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

    assert "qualcomm-ai-hub" in provider.name

    # If ONNX session failed to load (IR version mismatch), skip
    if provider._session is None:
        pytest.skip("ONNX model not available (IR version mismatch)")

    # Create synthetic test image
    img = Image.new("RGB", (600, 300), color="blue")
    img_bytes_io = io.BytesIO()
    img.save(img_bytes_io, format="PNG")
    raw_bytes = img_bytes_io.getvalue()

    analysis = await provider.analyze_figure(raw_bytes, "pipeline.png")
    assert analysis.figure_type in provider.classes
    assert len(analysis.observations) > 0
    assert analysis.confidence > 0.5

    qa_res = await provider.answer_question(raw_bytes, "Explain the diagram flow", "pipeline.png")
    assert "Qualcomm Vision Analysis" in qa_res.answer


def test_provider_factory_resolution():
    # Development backend
    dev_emb = get_embedding_provider("development")
    dev_llm = get_llm_provider("development")
    assert isinstance(dev_emb, DevelopmentEmbeddingProvider)
    assert isinstance(dev_llm, DevelopmentLLMProvider)

    # Qualcomm backend
    q_emb = get_embedding_provider("qualcomm")
    q_llm = get_llm_provider("qualcomm")
    assert isinstance(q_emb, QualcommEmbeddingProvider)
    assert isinstance(q_llm, QualcommLLMProvider)

    # Vision provider needs its ONNX artifact, and may also fail to load it.
    try:
        q_vis = get_vision_provider("qualcomm")
        assert isinstance(q_vis, QualcommVisionProvider)
    except QualcommModelUnavailable as e:
        pytest.skip(f"Vision model unavailable on this host: {e}")
    except RuntimeError as e:
        if "Unsupported model IR version" in str(e):
            pytest.skip("Vision model ONNX IR version mismatch")
        raise


def test_benchmark_harness_artifact_generation(tmp_path):
    artifact_path = run_full_benchmark(tmp_path, dry_run=True)
    assert artifact_path.exists()

    with open(artifact_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "timestamp_utc" in data
    assert "system_telemetry" in data
    assert "configuration" in data
    assert "benchmarks" in data

    bench = data["benchmarks"]
    assert "embedding" in bench
    assert "llm" in bench
    assert "application_e2e" in bench

    assert bench["embedding"]["cold_latency_ms"] >= 0
    assert bench["llm"]["cold_latency_ms"] >= 0
    assert bench["application_e2e"]["cold_e2e_latency_ms"] >= 0
