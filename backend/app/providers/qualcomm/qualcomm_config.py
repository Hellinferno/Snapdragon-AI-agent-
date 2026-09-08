"""Qualcomm AI Hub and Snapdragon execution configuration."""

from dataclasses import dataclass, field
from pathlib import Path
import platform
import os
from typing import List, Dict, Any, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


def _resolve_default_model_dir() -> Path:
    env_dir = os.getenv("QUALCOMM_MODEL_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.exists():
            return p
    candidates = [
        Path("models/qualcomm"),
        Path("backend/models/qualcomm"),
        Path(__file__).resolve().parents[3] / "models" / "qualcomm",
    ]
    for cand in candidates:
        if cand.exists():
            return cand
    return candidates[-1]


@dataclass
class QualcommConfig:
    """Configuration for Qualcomm Snapdragon AI runtime and models."""

    device_target: str = "auto"
    preferred_provider: str = "QNNExecutionProvider"
    fallback_provider: str = "CPUExecutionProvider"
    qnn_backend_path: str = "QnnHtp.dll"
    htp_performance_mode: str = "burst"
    htp_graph_optimization: str = "3"
    model_dir: Path = field(default_factory=_resolve_default_model_dir)

    # Qualcomm AI Hub verified candidate models
    embedding_model_id: str = "all-MiniLM-L6-v2"
    llm_model_id: str = "Qwen2.5-3B-Instruct"
    vision_model_id: str = "MobileNet-v2"

    # Precision
    precision: str = "int4"  # int4, int8, fp16

    def detect_host_environment(self) -> Dict[str, Any]:
        """Detect the current host system architecture and hardware environment."""
        uname = platform.uname()
        is_arm64 = uname.machine.lower() in ("arm64", "aarch64")
        is_windows = uname.system.lower() == "windows"

        available_providers = []
        try:
            import onnxruntime as ort
            available_providers = ort.get_available_providers()
        except ImportError:
            available_providers = []

        qnn_available = "QNNExecutionProvider" in available_providers

        detected_device = "Snapdragon Target PC" if (is_arm64 and is_windows) else f"{uname.system} {uname.machine}"
        if not is_arm64:
            detected_device += " (Development Host / Non-Snapdragon)"

        return {
            "system": uname.system,
            "machine": uname.machine,
            "processor": uname.processor,
            "is_arm64": is_arm64,
            "is_windows": is_windows,
            "available_providers": available_providers,
            "qnn_available": qnn_available,
            "detected_device": detected_device,
        }

    def get_effective_providers(self) -> List[Any]:
        """Returns the execution providers to pass to ONNX Runtime with appropriate fallback."""
        env = self.detect_host_environment()
        providers = []

        if env.get("qnn_available"):
            qnn_options = {
                "backend_path": self.qnn_backend_path,
                "htp_performance_mode": self.htp_performance_mode,
                "htp_graph_finalization_optimization_mode": self.htp_graph_optimization,
            }
            providers.append((self.preferred_provider, qnn_options))
            logger.info("Snapdragon QNN Hexagon NPU execution provider enabled.")
        else:
            logger.info(
                "QNNExecutionProvider not active on this host; falling back to %s.",
                self.fallback_provider,
            )

        providers.append(self.fallback_provider)
        return providers
