import platform

from fastapi import APIRouter

from app.core.config import settings
from app.providers.factory import (
    embedding_provider_status,
    llm_runs_locally,
    resolved_llm_name,
    resolved_vision_name,
    retrieval_mode,
)
from app.providers.qualcomm.qualcomm_config import QualcommConfig

router = APIRouter()


def _get_system_runtime_telemetry() -> dict:
    """Builds explicit hardware, accelerator, and privacy telemetry."""
    cfg = QualcommConfig()
    env = cfg.detect_host_environment()
    uname = platform.uname()

    qnn_active = env.get("qnn_available", False)
    active_provider = "QNNExecutionProvider" if qnn_active else "CPUExecutionProvider"
    backend = "Qualcomm Hexagon HTP" if qnn_active else "Host CPU"
    precision = "INT4" if qnn_active else "FP32"

    npu_status_label = "Hexagon NPU Active" if qnn_active else "Inactive (Host Development CPU)"
    runtime_mode = "Snapdragon Hexagon NPU" if qnn_active else "Development Host (CPU Simulation)"

    embedding = embedding_provider_status()
    llm_local = llm_runs_locally()
    vision_name = resolved_vision_name()
    vision_uses_model = vision_name.startswith("qualcomm-")

    # What actually executes each leg on this host, not what the target design uses.
    embedding_engine = (
        "feature hashing (embeddings, degraded)" if embedding.degraded else "ONNX Runtime (embeddings)"
    )
    vision_engine = "ONNX Runtime (vision)" if vision_uses_model else "pixel statistics (vision, no neural model)"
    if not llm_local:
        llm_engine = f"cloud API (LLM: {resolved_llm_name()})"
    elif resolved_llm_name().startswith("qualcomm-"):
        llm_engine = "QAIRT / GenieX (LLM; inference not implemented)"
    else:
        llm_engine = "template synthesizer (LLM placeholder)"
    runtime_engine = "; ".join([embedding_engine, vision_engine, llm_engine])

    privacy_checklist = [
        {"item": "Documents stored locally", "status": True, "detail": "Local SQLite database and filesystem storage"},
        {"item": "Embeddings stored locally", "status": True, "detail": f"384-d vector embeddings persisted on-device ({embedding.name})"},
        {"item": "Vector search local", "status": True, "detail": "Exact cosine similarity over SQLite-stored vectors, computed on the host CPU"},
        # The LLM is the only leg that can leave the machine; embeddings and vision never do.
        {
            "item": "AI inference local",
            "status": llm_local,
            "detail": (
                f"Embeddings and vision run locally on {backend} ({embedding.name}); "
                f"generation is served by {resolved_llm_name()}"
                if llm_local
                else f"Generation is served by the cloud provider {resolved_llm_name()}; "
                f"embeddings, retrieval and vision stay local"
            ),
        },
        {
            "item": "No document upload",
            "status": llm_local,
            "detail": (
                "No document content leaves the device"
                if llm_local
                else f"Documents are indexed locally, but retrieved excerpts are sent to "
                f"{resolved_llm_name()} for generation"
            ),
        },
        {"item": "External providers disabled", "status": not settings.ALLOW_EXTERNAL_PROVIDERS, "detail": "Cloud APIs blocked by default" if not settings.ALLOW_EXTERNAL_PROVIDERS else "External provider opted-in"},
    ]

    hardware_comparison = [
        {
            "model": "MiniLM-L6-v2 (Embedding)",
            "cpu": "all-MiniLM-L6-v2 (FP32)",
            "snapdragon_npu": "all-MiniLM-L6-v2 (ONNX Runtime + QNN; physical validation pending)",
            "benefit": "No benchmark published",
        },
        {
            "model": "Qwen3-4B-Instruct-2507 (LLM)",
            "cpu": "OpenRouter (development configuration)",
            "snapdragon_npu": "Qwen3-4B-Instruct-2507 (QAIRT / GenAI Inference Extensions; validation pending)",
            "benefit": "QAIRT inference not implemented",
        },
        {
            "model": "Vision (figure analysis)",
            "cpu": (
                f"{vision_name} (ONNX Runtime)"
                if vision_uses_model
                else "Pixel-statistics analysis (no neural model)"
            ),
            "snapdragon_npu": "MobileNet-v2 (ONNX Runtime + QNN; no trained figure classifier yet, validation pending)",
            "benefit": "No benchmark published",
        },
        {
            "model": "Runtime paths",
            "cpu": "CPUExecutionProvider",
            "snapdragon_npu": "QNNExecutionProvider (embeddings/vision); QAIRT (LLM, pending)",
            "benefit": "Separate runtimes",
        },
    ]

    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "device_name": env.get("detected_device"),
        "processor": uname.processor or "Unknown",
        "architecture": uname.machine,
        "runtime_engine": runtime_engine,
        "active_provider": active_provider,
        "execution_backend": backend,
        "precision": precision,
        "hardware_npu_active": qnn_active,
        "npu_status": npu_status_label,
        "runtime_mode": runtime_mode,
        "provider_backend": settings.PROVIDER_BACKEND,
        # Resolved providers, not the configured strings: a machine without the ONNX
        # model must not be able to look like it is running semantic retrieval.
        "llm_provider": resolved_llm_name(),
        "embedding_provider": embedding.name,
        "embedding_backend": embedding.backend,
        "embedding_degraded": embedding.degraded,
        "embedding_degraded_reason": embedding.reason,
        "retrieval_mode": retrieval_mode(),
        "vision_provider": vision_name,
        "llm_runs_locally": llm_local,
        "external_providers_enabled": settings.ALLOW_EXTERNAL_PROVIDERS,
        "device_target": settings.QUALCOMM_DEVICE_TARGET,
        "privacy_checklist": privacy_checklist,
        "hardware_benchmark_comparison": hardware_comparison,
        "hardware_validation_note": "Qwen3-4B-Instruct-2507 QAIRT bundle detection and tokenizer loading are implemented. QAIRT inference, physical Snapdragon validation, and NPU benchmarks are pending; no Snapdragon LLM performance is reported.",
    }


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint confirming service and AI provider runtime status."""
    return _get_system_runtime_telemetry()


@router.get("/runtime/status")
async def runtime_status() -> dict:
    """Detailed hardware, NPU, and privacy telemetry status."""
    return _get_system_runtime_telemetry()
