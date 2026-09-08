import os
import re
from app.providers.base import GenerationResult, LLMProvider


class DevelopmentLLMProvider(LLMProvider):
    """
    Deterministic, grounded evidence synthesizer.
    Generates structured answers based strictly on retrieved source chunks,
    guarantees factual citations, and refuses to hallucinate when evidence is insufficient.
    """

    @property
    def name(self) -> str:
        return "development-grounded-synthesizer"

    async def generate(self, prompt: str, system_prompt: str | None = None) -> GenerationResult:
        # Check if external API is configured
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            return await self._call_external_openai(prompt, system_prompt, api_key)

        return self._synthesize_grounded_answer(prompt)

    def _synthesize_grounded_answer(self, prompt: str) -> GenerationResult:
        # Parse context and question from the structured prompt
        context_match = re.search(r"### CONTEXT:\n(.*?)\n### QUESTION:\n(.*?)$", prompt, re.DOTALL)
        if not context_match:
            context_text = prompt
            question = ""
        else:
            context_text = context_match.group(1).strip()
            question = context_match.group(2).strip()

        # Check for insufficient evidence marker
        if not context_text or "NO_RELEVANT_EVIDENCE" in context_text:
            refusal_text = (
                "Insufficient evidence in the indexed documents to answer this question. "
                "The documents in your library do not contain information directly addressing this query."
            )
            return GenerationResult(text=refusal_text, prompt_tokens=len(prompt.split()), completion_tokens=len(refusal_text.split()))

        # Extract source blocks [Source N: "Title", Page X, Section: "Sec"]
        blocks = re.split(r"\[Source \d+: (.*?)\]", context_text)
        sources_meta: list[str] = []
        sources_content: list[str] = []

        for i in range(1, len(blocks), 2):
            sources_meta.append(blocks[i].strip())
            sources_content.append(blocks[i + 1].strip() if i + 1 < len(blocks) else "")

        if not sources_content:
            return GenerationResult(
                text="Insufficient evidence in the indexed documents to answer this question.",
                prompt_tokens=len(prompt.split()),
                completion_tokens=15,
            )

        # Synthesize answer from the highest relevance sources
        answer_paragraphs: list[str] = []
        answer_paragraphs.append(
            f"Based on the indexed research material, here is what the evidence indicates regarding your inquiry:\n"
        )

        for meta, content in zip(sources_meta, sources_content, strict=False):
            # Clean snippet for synthesis
            clean_snippet = content.replace("\n", " ").strip()
            # Trim to key sentence if lengthy
            sentences = [s.strip() for s in clean_snippet.split(". ") if len(s.strip()) > 15]
            summary_sentence = ". ".join(sentences[:2])
            if summary_sentence and not summary_sentence.endswith("."):
                summary_sentence += "."

            if summary_sentence:
                answer_paragraphs.append(f"• {summary_sentence} [{meta}]")

        answer_text = "\n\n".join(answer_paragraphs)

        return GenerationResult(
            text=answer_text,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(answer_text.split()),
        )

    async def _call_external_openai(self, prompt: str, system_prompt: str | None, api_key: str) -> GenerationResult:
        import httpx

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are ScholarEdge, a strict grounded research copilot."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return GenerationResult(
                text=choice,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )


# Global singleton instance
llm_provider: LLMProvider = DevelopmentLLMProvider()
