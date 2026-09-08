from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmbeddingResult:
    vector: list[float]
    dimension: int


@dataclass
class GenerationResult:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class EmbeddingProvider(ABC):
    """Abstract interface for generating text embeddings."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension."""
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector for a single text chunk."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of text chunks."""
        pass


class LLMProvider(ABC):
    """Abstract interface for text generation."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str | None = None) -> GenerationResult:
        """Generate response from text prompt."""
        pass


class OCRProvider(ABC):
    """Abstract interface for optical character recognition."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass

    @abstractmethod
    async def extract_text_from_image(self, image_bytes: bytes) -> str:
        """Extract text from image bytes."""
        pass
