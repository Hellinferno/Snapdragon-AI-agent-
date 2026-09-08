import hashlib
import math
import re
from app.providers.base import EmbeddingProvider


# Common English stopwords to reduce noise in feature hashing
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "were",
    "will", "with", "this", "these", "those", "we", "our", "you", "they",
}


class DevelopmentEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic, high-dimension feature hashing embedding provider.
    Produces 384-dimensional unit-normalized vectors suitable for local semantic
    retrieval during development, tests, and lightweight deployments without
    requiring multi-gigabyte neural weight downloads.
    """

    def __init__(self, dim: int = 384):
        self._dim = dim

    @property
    def name(self) -> str:
        return "development-feature-hash-384"

    @property
    def dimension(self) -> int:
        return self._dim

    def _tokenize(self, text: str) -> list[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower())
        return [w for w in words if w not in STOPWORDS]

    async def embed_text(self, text: str) -> list[float]:
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self._dim

        vector = [0.0] * self._dim

        # Unigrams & bigrams
        ngrams: list[str] = list(tokens)
        for i in range(len(tokens) - 1):
            ngrams.append(f"{tokens[i]}_{tokens[i+1]}")

        for item in ngrams:
            # Hash to bucket index and sign
            h = hashlib.sha256(item.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "big") % self._dim
            sign = 1.0 if (h[4] % 2 == 0) else -1.0
            vector[idx] += sign

        # Normalize to L2 unit norm
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [round(x / norm, 6) for x in vector]

        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            vec = await self.embed_text(text)
            results.append(vec)
        return results


# Global singleton instance
embedding_provider: EmbeddingProvider = DevelopmentEmbeddingProvider()
