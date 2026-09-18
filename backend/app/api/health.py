import platform
from fastapi import APIRouter
from app.core.config import settings
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

    privacy_checklist = [
        {"item": "Documents stored locally", "status": True, "detail": "Local SQLite database and filesystem storage"},
        {"item": "Embeddings stored locally", "status": True, "detail": "384-d vector embeddings persisted on-device"},
        {"item": "Vector search local", "status": True, "detail": "Local SQLite exact cosine similarity"},
        {"item": "AI inference local", "status": True, "detail": f"ONNX Runtime on {backend} for embeddings and vision; QAIRT LLM validation pending"},
        {"item": "No document upload", "status": True, "detail": "Zero document transmission to third-party endpoints"},
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
            "model": "MobileNet-v2 (Vision)",
            "cpu": "MobileNet-v2 (FP32)",
            "snapdragon_npu": "MobileNet-v2 (ONNX Runtime + QNN; physical validation pending)",
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
        "runtime_engine": "ONNX Runtime (embeddings/vision); QAIRT pending (LLM)",
        "active_provider": active_provider,
        "execution_backend": backend,
        "precision": precision,
        "hardware_npu_active": qnn_active,
        "npu_status": npu_status_label,
        "runtime_mode": runtime_mode,
        "provider_backend": settings.PROVIDER_BACKEND,
        "llm_provider": settings.LLM_PROVIDER or settings.PROVIDER_BACKEND,
        "embedding_provider": settings.EMBEDDING_PROVIDER or settings.PROVIDER_BACKEND,
        "vision_provider": settings.VISION_PROVIDER or settings.PROVIDER_BACKEND,
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
