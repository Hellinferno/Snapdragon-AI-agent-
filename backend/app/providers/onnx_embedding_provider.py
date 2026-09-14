"""Sentence embeddings from the real all-MiniLM-L6-v2 ONNX export via ONNX Runtime (CPU).

Uses the model's own WordPiece tokenizer, mean pooling over the attention mask and L2
normalization, matching sentence-transformers' reference pipeline. Download the weights
with scripts/download_embedding_model.py.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np

from app.providers.base import EmbeddingProvider

MAX_TOKENS = 256  # the length all-MiniLM-L6-v2 was trained with
BATCH_SIZE = 32


class OnnxMiniLMEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_dir: Path):
        model_path = model_dir / "model.onnx"
        tokenizer_path = model_dir / "tokenizer.json"
        if not model_path.exists() or not tokenizer_path.exists():
            raise FileNotFoundError(
                f"all-MiniLM-L6-v2 not found in {model_dir}. Run: python scripts/download_embedding_model.py"
            )

        import onnxruntime as ort
        from tokenizers import Tokenizer

        self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self._tokenizer.enable_truncation(max_length=MAX_TOKENS)
        self._tokenizer.enable_padding(pad_id=self._tokenizer.token_to_id("[PAD]"), pad_token="[PAD]")
        self._session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self._input_names = {i.name for i in self._session.get_inputs()}

    @property
    def name(self) -> str:
        return "onnx-all-MiniLM-L6-v2"

    @property
    def dimension(self) -> int:
        return 384

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            encodings = self._tokenizer.encode_batch(texts[start : start + BATCH_SIZE])
            ids = np.array([e.ids for e in encodings], dtype=np.int64)
            mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
            feeds = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self._input_names:
                feeds["token_type_ids"] = np.array([e.type_ids for e in encodings], dtype=np.int64)

            hidden = self._session.run(["last_hidden_state"], feeds)[0]
            weights = mask[..., None].astype(np.float32)
            pooled = (hidden * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
            pooled /= np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12, None)
            vectors.extend(np.round(pooled, 6).tolist())
        return vectors

    async def embed_text(self, text: str) -> list[float]:
        return (await self.embed_batch([text]))[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Inference is CPU-bound; keep the event loop responsive during ingestion
        return await asyncio.to_thread(self._embed_sync, texts)
