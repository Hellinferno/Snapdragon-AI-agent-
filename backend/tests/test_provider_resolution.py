"""Provider resolution: auto-selection, explicit overrides, and honest telemetry.

The rule under test is that auto-selection happens *only* when nothing was
configured. That distinction is what lets a fresh checkout get the real embedding
model while the hermetic suite (which sets EMBEDDING_PROVIDER explicitly) stays
deterministic.
"""

import pytest

from app.core.config import settings
from app.providers import factory
from app.providers.embedding_provider import DevelopmentEmbeddingProvider
from app.providers.factory import (
    DEGRADED_EMBEDDING_REASON,
    embedding_provider_status,
    effective_hybrid_retrieval,
    get_embedding_provider,
    llm_runs_locally,
    resolved_embedding_backend,
    resolved_llm_name,
    resolved_vision_name,
    retrieval_mode,
    semantic_embeddings_available,
)

MODEL_READY = semantic_embeddings_available()


def _configure(monkeypatch, *, embedding=None, provider_backend="development", hybrid=None, llm=None):
    """Simulates a configuration, marking fields as explicitly provided."""
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", embedding)
    monkeypatch.setattr(settings, "PROVIDER_BACKEND", provider_backend)
    monkeypatch.setattr(settings, "HYBRID_RETRIEVAL", hybrid)
    monkeypatch.setattr(settings, "LLM_PROVIDER", llm)


def _simulate_no_configuration(monkeypatch):
    """A fresh checkout: no .env, so nothing counts as explicitly selected.

    The developer's own .env sets PROVIDER_BACKEND, which pydantic marks as
    explicitly provided; that flag is read-only, so the check is injected instead.
    """
    monkeypatch.setattr(factory, "_provider_backend_was_explicitly_set", lambda: False)


# ---------------------------------------------------------------------------
# A1: auto-selection vs explicit configuration
# ---------------------------------------------------------------------------


def test_unset_backend_prefers_the_semantic_model_when_available(monkeypatch):
    if not MODEL_READY:
        pytest.skip("MiniLM model not downloaded: run scripts/download_embedding_model.py")

    _configure(monkeypatch, embedding=None)
    _simulate_no_configuration(monkeypatch)

    assert resolved_embedding_backend() == "onnx_minilm"
    assert get_embedding_provider().name == "onnx-all-MiniLM-L6-v2"


def test_unset_backend_falls_back_to_hashing_when_the_model_is_missing(monkeypatch):
    _configure(monkeypatch, embedding=None)
    _simulate_no_configuration(monkeypatch)
    monkeypatch.setattr(settings, "EMBEDDING_MODEL_DIR", settings.EMBEDDING_MODEL_DIR / "does-not-exist")

    provider = get_embedding_provider()

    assert isinstance(provider, DevelopmentEmbeddingProvider)
    assert provider.is_semantic is False
    assert resolved_embedding_backend() == "development"


def test_explicit_development_is_never_upgraded_to_the_semantic_model(monkeypatch):
    """Determinism on request: an explicit development backend stays hashing."""
    if not MODEL_READY:
        pytest.skip("MiniLM model not downloaded: run scripts/download_embedding_model.py")

    _configure(monkeypatch, embedding="development")

    provider = get_embedding_provider()

    assert isinstance(provider, DevelopmentEmbeddingProvider)
    assert resolved_embedding_backend() == "development"


def test_explicit_backend_via_provider_backend_is_honored(monkeypatch):
    """PROVIDER_BACKEND=qualcomm is an explicit choice, not an absent configuration."""
    _configure(monkeypatch, embedding=None, provider_backend="qualcomm")

    assert resolved_embedding_backend() == "qualcomm"


def test_missing_model_raises_when_semantic_embeddings_are_explicitly_requested(monkeypatch):
    """An explicit request must fail loudly instead of silently degrading."""
    _configure(monkeypatch, embedding="onnx_minilm")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL_DIR", settings.EMBEDDING_MODEL_DIR / "does-not-exist")

    with pytest.raises(FileNotFoundError, match="download_embedding_model"):
        get_embedding_provider()


# ---------------------------------------------------------------------------
# A1: the label map used for cheap telemetry must not drift from the providers
# ---------------------------------------------------------------------------


def test_embedding_labels_match_the_real_providers():
    assert factory.EMBEDDING_LABELS["development"] == DevelopmentEmbeddingProvider().name

    if MODEL_READY:
        from app.providers.onnx_embedding_provider import OnnxMiniLMEmbeddingProvider

        assert factory.EMBEDDING_LABELS["onnx_minilm"] == OnnxMiniLMEmbeddingProvider(
            settings.EMBEDDING_MODEL_DIR
        ).name


# ---------------------------------------------------------------------------
# A2: the hybrid default follows the resolved embedding provider
# ---------------------------------------------------------------------------


def test_hybrid_default_is_on_for_hash_and_off_for_semantic_embeddings(monkeypatch):
    _configure(monkeypatch, embedding="development", hybrid=None)
    assert effective_hybrid_retrieval() is True

    _configure(monkeypatch, embedding="onnx_minilm", hybrid=None)
    assert effective_hybrid_retrieval() is False


def test_explicit_hybrid_setting_always_wins(monkeypatch):
    _configure(monkeypatch, embedding="development", hybrid=False)
    assert effective_hybrid_retrieval() is False

    _configure(monkeypatch, embedding="onnx_minilm", hybrid=True)
    assert effective_hybrid_retrieval() is True


def test_retrieval_mode_labels_the_active_configuration(monkeypatch):
    _configure(monkeypatch, embedding="development", hybrid=None)
    assert retrieval_mode() == "lexical-hash-hybrid"

    _configure(monkeypatch, embedding="onnx_minilm", hybrid=None)
    assert retrieval_mode() == "semantic-vector"


# ---------------------------------------------------------------------------
# A3/A4: status and telemetry report what is running, not what was configured
# ---------------------------------------------------------------------------


def test_status_flags_the_hash_fallback_as_degraded(monkeypatch):
    _configure(monkeypatch, embedding="development")

    status = embedding_provider_status()

    assert status.degraded is True
    assert status.reason == DEGRADED_EMBEDDING_REASON
    assert status.name == "development-feature-hash-384"


def test_status_is_not_degraded_for_semantic_embeddings(monkeypatch):
    if not MODEL_READY:
        pytest.skip("MiniLM model not downloaded: run scripts/download_embedding_model.py")

    _configure(monkeypatch, embedding="onnx_minilm")

    status = embedding_provider_status()

    assert status.degraded is False
    assert status.reason is None
    assert status.name == "onnx-all-MiniLM-L6-v2"


def test_resolved_names_reflect_the_configured_backend(monkeypatch):
    _configure(monkeypatch, embedding="development", llm="openrouter")
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", "qwen/test-model")

    assert resolved_llm_name() == "openrouter-qwen/test-model"
    assert llm_runs_locally() is False

    _configure(monkeypatch, embedding="development", llm="development")
    assert resolved_llm_name() == "development-grounded-synthesizer"
    assert llm_runs_locally() is True


def test_vision_provider_name_defaults_to_the_local_heuristic(monkeypatch):
    _configure(monkeypatch, embedding="development")
    monkeypatch.setattr(settings, "VISION_PROVIDER", None)

    assert resolved_vision_name() == "development-vision-heuristic"
