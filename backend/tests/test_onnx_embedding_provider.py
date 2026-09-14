"""Exercises the real all-MiniLM-L6-v2 model when it has been downloaded (skipped otherwise, e.g. on CI)."""

import numpy as np
import pytest

from app.core.config import settings

pytestmark = pytest.mark.skipif(
    not (settings.EMBEDDING_MODEL_DIR / "model.onnx").exists(),
    reason="run scripts/download_embedding_model.py to enable",
)


@pytest.fixture(scope="module")
def provider():
    from app.providers.onnx_embedding_provider import OnnxMiniLMEmbeddingProvider

    return OnnxMiniLMEmbeddingProvider(settings.EMBEDDING_MODEL_DIR)


@pytest.mark.asyncio
async def test_vectors_are_unit_norm_and_batch_matches_single(provider):
    texts = ["Overfitting hurts generalization.", "", "word " * 600]  # empty and over-length inputs
    batch = await provider.embed_batch(texts)
    assert [len(v) for v in batch] == [384, 384, 384]
    assert all(abs(np.linalg.norm(v) - 1.0) < 1e-3 for v in batch)
    single = await provider.embed_text(texts[0])
    assert np.allclose(single, batch[0], atol=1e-4)  # padding in a batch must not change the vector


@pytest.mark.asyncio
async def test_paraphrase_is_closer_than_unrelated_text(provider):
    query, paraphrase, unrelated = await provider.embed_batch([
        "How does the book define overfitting?",
        "Overfitting is the tendency of data mining procedures to tailor models to the training data.",
        "Strawberry Pop-Tarts sales increased ahead of the hurricane.",
    ])
    assert np.dot(query, paraphrase) > np.dot(query, unrelated) + 0.2


def test_missing_model_dir_raises_actionable_error(tmp_path):
    from app.providers.onnx_embedding_provider import OnnxMiniLMEmbeddingProvider

    with pytest.raises(FileNotFoundError, match="download_embedding_model"):
        OnnxMiniLMEmbeddingProvider(tmp_path)
