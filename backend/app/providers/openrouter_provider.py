"""Explicit OpenRouter-backed generation provider."""

import os
import ssl

import httpx
from app.core.config import settings
from app.providers.base import GenerationResult, LLMProvider


class OpenRouterProvider(LLMProvider):
    """Uses OpenRouter API when the application explicitly selects this provider."""

    @property
    def name(self) -> str:
        return f"openrouter-{settings.OPENROUTER_MODEL}"

    async def generate(self, prompt: str, system_prompt: str | None = None) -> GenerationResult:
        api_key = settings.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OpenRouter is selected but OPENROUTER_API_KEY is not configured.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.OPENROUTER_MODEL,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": settings.OPENROUTER_MAX_TOKENS,
        }



        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://scholaredge.local",
            "X-Title": "ScholarEdge",
        }

        url = "https://openrouter.ai/api/v1/chat/completions"
        # Verify against the OS trust store rather than certifi's bundle, so machines whose
        # antivirus or corporate proxy re-signs TLS (trusted by the OS) can still connect.
        async with httpx.AsyncClient(timeout=45.0, verify=ssl.create_default_context()) as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenRouter returned no generation choices.")

        content = choices[0].get("message", {}).get("content", "").strip()
        if not content:
            raise RuntimeError("OpenRouter returned an empty response.")

        usage = data.get("usage", {})
        return GenerationResult(
            text=content,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )
