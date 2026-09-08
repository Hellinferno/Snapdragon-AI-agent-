"""Explicit Gemini-backed generation provider."""

import os

import httpx

from app.core.config import settings
from app.providers.base import GenerationResult, LLMProvider


class GeminiLLMProvider(LLMProvider):
    """Uses Gemini only when the application explicitly selects this provider."""

    @property
    def name(self) -> str:
        return f"gemini-{settings.GEMINI_MODEL}"

    async def generate(self, prompt: str, system_prompt: str | None = None) -> GenerationResult:
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Gemini is selected but GEMINI_API_KEY is not configured.")

        payload: dict[str, object] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": api_key},
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned no generation candidates.")

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response.")

        usage = data.get("usageMetadata", {})
        return GenerationResult(
            text=text,
            prompt_tokens=usage.get("promptTokenCount", 0),
            completion_tokens=usage.get("candidatesTokenCount", 0),
        )
