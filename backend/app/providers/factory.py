"""Central Provider Factory resolving AI providers based on configuration.

Two resolution rules here are deliberate and load-bearing:

1. Auto-selection happens *only* when no backend was configured. A fresh checkout
   with no `.env` gets the real all-MiniLM-L6-v2 model when it can actually be
   loaded, so the out-of-the-box retrieval quality is the good one. Anything
   explicitly configured — including an explicit "development" — is honored
   exactly, which is what keeps CI and the hermetic test suite deterministic.
2. The hybrid-retrieval default follows the resolved embedding provider, because
   the two configurations want opposite settings (see `effective_hybrid_retrieval`).
"""

import importlib.util
from dataclasses import asdict, dataclass
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.providers.base import EmbeddingProvider, LLMProvider, VisionProvider, OCRProvider
from app.providers.embedding_provider import DevelopmentEmbeddingProvider
from app.providers.gemini_provider import GeminiLLMProvider
from app.providers.openrouter_provider import OpenRouterProvider
from app.providers.llm_provider import DevelopmentLLMProvider
from app.providers.vision_provider import DevelopmentVisionProvider, DevelopmentOCRProvider
from app.providers.qualcomm.qualcomm_config import QualcommConfig
from app.providers.qualcomm.qualcomm_providers import (
    QualcommEmbeddingProvider,
    QualcommLLMProvider,
    QualcommVisionProvider,
)

logger = get_logger(__name__)

ONNX_EMBEDDING_BACKEND = "onnx_minilm"
QUALCOMM_BACKEND = "qualcomm"
DEVELOPMENT_BACKEND = "development"

# Display names for the cheap, no-weights-loading path. `test_provider_resolution`
# pins these against the providers' own `name` so they cannot drift silently.
EMBEDDING_LABELS = {
    DEVELOPMENT_BACKEND: "development-feature-hash-384",
    ONNX_EMBEDDING_BACKEND: "onnx-all-MiniLM-L6-v2",
}
REMOTE_LLM_BACKENDS = {"openrouter", "openrouter_api", "gemini"}

DEGRADED_EMBEDDING_REASON = (
    "Semantic embeddings are unavailable, so retrieval uses sha256 feature hashing. "
    "Run `python scripts/download_embedding_model.py`, then "
    "`python scripts/reindex_embeddings.py`, to enable onnx_minilm."
)


@dataclass(frozen=True)
class EmbeddingProviderStatus:
    """What the embedding path is actually doing, as opposed to what it was told to do."""

    backend: str
    name: str
    degraded: bool
    reason: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def _onnx_artifacts_present() -> bool:
    return all(
        (settings.EMBEDDING_MODEL_DIR / filename).exists()
        for filename in ("model.onnx", "tokenizer.json")
    )


def _onnx_runtime_installed() -> bool:
    return all(
        importlib.util.find_spec(module) is not None
        for module in ("onnxruntime", "tokenizers")
    )


def semantic_embeddings_available() -> bool:
    """Whether onnx_minilm can be used here, checked without loading the 90 MB model."""
    return _onnx_artifacts_present() and _onnx_runtime_installed()


def _provider_backend_was_explicitly_set() -> bool:
    """Whether PROVIDER_BACKEND came from configuration rather than its default.

    Pydantic records fields supplied by the environment or a .env file, so a global
    backend selection is distinguishable from an absent one. Isolated here so tests
    can simulate a machine with no configuration at all.
    """
    return "PROVIDER_BACKEND" in settings.model_fields_set


def _requested_embedding_backend() -> str | None:
    """The embedding backend an operator explicitly asked for, if any.

    EMBEDDING_PROVIDER wins. Otherwise a PROVIDER_BACKEND that was explicitly
    provided (environment, .env, or a test override) is honored, so selecting
    "qualcomm" globally — or deliberately pinning "development" for
    reproducibility — still means what it says. Returns None when neither was set,
    which is the cue for the caller to pick the best available local backend.
    """
    if settings.EMBEDDING_PROVIDER:
        return settings.EMBEDDING_PROVIDER.strip().lower()
    if _provider_backend_was_explicitly_set() and settings.PROVIDER_BACKEND:
        return settings.PROVIDER_BACKEND.strip().lower()
    return None


def resolved_embedding_backend() -> str:
    """Which embedding backend is in use: 'qualcomm', 'onnx_minilm', or 'development'."""
    requested = _requested_embedding_backend()
    if requested:
        return requested
    return ONNX_EMBEDDING_BACKEND if semantic_embeddings_available() else DEVELOPMENT_BACKEND


def get_embedding_provider(backend: Optional[str] = None) -> EmbeddingProvider:
    """Return the configured EmbeddingProvider."""
    explicitly_requested = bool(backend) or _requested_embedding_backend() is not None
    effective_backend = (backend or resolved_embedding_backend()).lower()

    if effective_backend == QUALCOMM_BACKEND:
        logger.info("Instantiating QualcommEmbeddingProvider (Snapdragon target).")
        cfg = QualcommConfig(
            device_target=settings.QUALCOMM_DEVICE_TARGET,
            model_dir=settings.QUALCOMM_MODEL_DIR,
            qnn_backend_path=settings.QUALCOMM_BACKEND_PATH,
            htp_performance_mode=settings.QUALCOMM_PERFORMANCE_MODE,
        )
        return QualcommEmbeddingProvider(cfg)

    if effective_backend == ONNX_EMBEDDING_BACKEND:
        from app.providers.onnx_embedding_provider import OnnxMiniLMEmbeddingProvider

        try:
            return OnnxMiniLMEmbeddingProvider(settings.EMBEDDING_MODEL_DIR)
        except Exception as exc:  # missing weights, or onnxruntime/tokenizers not installed
            if explicitly_requested:
                # An explicit request must fail loudly rather than silently degrade.
                raise
            logger.warning(
                "all-MiniLM-L6-v2 was selected automatically but could not be loaded (%s: %s); "
                "falling back to %s. %s",
                type(exc).__name__,
                exc,
                EMBEDDING_LABELS[DEVELOPMENT_BACKEND],
                DEGRADED_EMBEDDING_REASON,
            )
            return DevelopmentEmbeddingProvider()

    if not explicitly_requested:
        logger.warning("No semantic embedding backend is configured. %s", DEGRADED_EMBEDDING_REASON)
    return DevelopmentEmbeddingProvider()


_LABEL_TO_BACKEND = {label: backend for backend, label in EMBEDDING_LABELS.items()}


def describe_embedding_provider(embedding: EmbeddingProvider) -> EmbeddingProviderStatus:
    """Status for an already-resolved provider, so recorded results match what ran.

    `embedding_provider_status` answers "what would be resolved" without loading any
    weights (used by /health); this answers "what is running" for a given instance
    (used when freezing an evaluation result).
    """
    degraded = not embedding.is_semantic
    return EmbeddingProviderStatus(
        backend=_LABEL_TO_BACKEND.get(embedding.name, embedding.name),
        name=embedding.name,
        degraded=degraded,
        reason=DEGRADED_EMBEDDING_REASON if degraded else None,
    )


def embedding_provider_status() -> EmbeddingProviderStatus:
    """The resolved embedding backend, with an explicit degraded flag.

    Reported by /health and recorded in evaluation result files so a weak run can
    never be quoted as if it were a semantic one.
    """
    backend = resolved_embedding_backend()
    if backend == QUALCOMM_BACKEND:
        name = f"qualcomm-ai-hub-{QualcommConfig().embedding_model_id}"
    else:
        name = EMBEDDING_LABELS.get(backend, backend)

    degraded = backend == DEVELOPMENT_BACKEND
    return EmbeddingProviderStatus(
        backend=backend,
        name=name,
        degraded=degraded,
        reason=DEGRADED_EMBEDDING_REASON if degraded else None,
    )


def effective_hybrid_retrieval(embedding: EmbeddingProvider | None = None) -> bool:
    """Whether BM25 keyword ranking is fused with vector ranking.

    An explicit HYBRID_RETRIEVAL always wins. Left unset, the default follows the
    resolved embedding provider, because the two configurations want opposite
    settings: measured on the book corpus, BM25 fusion costs a retrieval hit with
    real semantic embeddings (94.4% -> 83.3% answer correctness) while it is the
    single largest gain with the feature-hash fallback (44.4% -> 72.2%). Leaving it
    on unconditionally would put a fresh checkout on the second-best configuration.
    See evaluation/README.md for the full matrix.
    """
    if settings.HYBRID_RETRIEVAL is not None:
        return settings.HYBRID_RETRIEVAL
    if embedding is not None:
        return not embedding.is_semantic
    # Decided from the resolved backend so callers such as /health never pay to
    # construct (and load) the embedding model just to report a setting.
    return resolved_embedding_backend() not in (ONNX_EMBEDDING_BACKEND, QUALCOMM_BACKEND)


def retrieval_mode(embedding: EmbeddingProvider | None = None) -> str:
    """Label for how search is actually configured, e.g. 'semantic-vector'."""
    if embedding is not None:
        semantic = embedding.is_semantic
    else:
        semantic = resolved_embedding_backend() != DEVELOPMENT_BACKEND
    family = "semantic" if semantic else "lexical-hash"
    return f"{family}-{'hybrid' if effective_hybrid_retrieval(embedding) else 'vector'}"


def resolved_llm_name() -> str:
    """Name of the LLM provider the configuration selects, without constructing it."""
    backend = (settings.LLM_PROVIDER or settings.PROVIDER_BACKEND or "").strip().lower()
    if backend in ("openrouter", "openrouter_api"):
        return f"openrouter-{settings.OPENROUTER_MODEL}"
    if backend == "gemini":
        return f"gemini-{settings.GEMINI_MODEL}"
    if backend == QUALCOMM_BACKEND:
        return f"qualcomm-ai-hub-{QualcommConfig().llm_model_id}"
    return "development-grounded-synthesizer"


def resolved_vision_name() -> str:
    """Name of the vision provider the configuration selects."""
    backend = (settings.VISION_PROVIDER or settings.PROVIDER_BACKEND or "").strip().lower()
    if backend == QUALCOMM_BACKEND:
        return f"qualcomm-ai-hub-{QualcommConfig().vision_model_id}"
    return "development-vision-heuristic"


def llm_runs_locally() -> bool:
    """False when generation is delegated to a cloud provider (OpenRouter/Gemini).

    Embeddings, retrieval and vision stay local in every configuration; this is the
    only leg that can leave the machine, and /health must not claim otherwise.
    """
    backend = (settings.LLM_PROVIDER or settings.PROVIDER_BACKEND or "").strip().lower()
    return backend not in REMOTE_LLM_BACKENDS


def get_llm_provider(backend: Optional[str] = None) -> LLMProvider:
    """Return the configured LLMProvider."""
    effective_backend = (backend or settings.LLM_PROVIDER or settings.PROVIDER_BACKEND).lower()
    if effective_backend in ("openrouter", "openrouter_api"):
        if not settings.ALLOW_EXTERNAL_PROVIDERS:
            raise ValueError(
                "External cloud providers are disabled by default to guarantee local privacy. "
                "Set ALLOW_EXTERNAL_PROVIDERS=true in your environment to explicitly opt-in."
            )
        return OpenRouterProvider()
    if effective_backend == "gemini":
        if not settings.ALLOW_EXTERNAL_PROVIDERS:
            raise ValueError(
                "External cloud providers are disabled by default to guarantee local privacy. "
                "Set ALLOW_EXTERNAL_PROVIDERS=true in your environment to explicitly opt-in."
            )
        return GeminiLLMProvider()

    if effective_backend == "qualcomm":
        logger.info("Instantiating QualcommLLMProvider (Snapdragon target).")
        cfg = QualcommConfig(
            device_target=settings.QUALCOMM_DEVICE_TARGET,
            model_dir=settings.QUALCOMM_MODEL_DIR,
            qnn_backend_path=settings.QUALCOMM_BACKEND_PATH,
            htp_performance_mode=settings.QUALCOMM_PERFORMANCE_MODE,
        )
        return QualcommLLMProvider(cfg)
    return DevelopmentLLMProvider()


def get_vision_provider(backend: Optional[str] = None) -> VisionProvider:
    """Return the configured VisionProvider."""
    effective_backend = (backend or settings.VISION_PROVIDER or settings.PROVIDER_BACKEND).lower()
    if effective_backend == "qualcomm":
        logger.info("Instantiating QualcommVisionProvider (Snapdragon target).")
        cfg = QualcommConfig(
            device_target=settings.QUALCOMM_DEVICE_TARGET,
            model_dir=settings.QUALCOMM_MODEL_DIR,
            qnn_backend_path=settings.QUALCOMM_BACKEND_PATH,
            htp_performance_mode=settings.QUALCOMM_PERFORMANCE_MODE,
        )
        return QualcommVisionProvider(cfg)
    return DevelopmentVisionProvider()


def get_ocr_provider(backend: Optional[str] = None) -> OCRProvider:
    """Return the configured OCRProvider."""
    return DevelopmentOCRProvider()
