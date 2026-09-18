import json
import random
import re
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.providers.base import LLMProvider
from app.providers.factory import get_llm_provider
from app.schemas.learning import (
    ExplainResponse,
    Flashcard,
    FlashcardsResponse,
    QuizQuestion,
    QuizResponse,
)
from app.schemas.rag import SourceReference
from app.services.context_builder import build_context_block
from app.services.retrieval_service import RetrievalService

logger = get_logger(__name__)

# Distance below which a chunk is considered too weak to be used as grounding
# material for LLM-generated learning content.
MIN_GROUNDING_SCORE = 0.05

EXPLAIN_SYSTEM_PROMPT = """You are ScholarEdge, a private on-device research tutor.
Explain the requested concept using ONLY the CONTEXT blocks provided.

RULES:
1. Use ONLY facts present in the CONTEXT. Never add outside knowledge.
2. For every factual claim cite the source: [Doc: <title>, Page: <N>].
3. If the context is insufficient, state exactly what evidence is missing instead of speculating.
4. Write the explanation in clear prose (3-6 sentences for beginner, 5-8 for intermediate,
   6-10 with caveats for deep_dive), then a line "KEY TAKEAWAYS:" followed by 2-4 bullet
   lines, each starting with "- ".
"""

LEVEL_STYLE = {
    "beginner": (
        "Explain for a complete newcomer: plain language, one everyday analogy, no unexplained jargon."
    ),
    "intermediate": (
        "Explain for a technically literate reader: precise terminology, mechanism, and how it is used in the cited studies."
    ),
    "deep_dive": (
        "Provide a deep-dive: exact mechanisms, quantitative results from the context, methodological caveats, and open limitations."
    ),
}

QUIZ_SYSTEM_PROMPT = """You are ScholarEdge, a private on-device research quiz generator.
Create multiple-choice quiz questions grounded STRICTLY in the CONTEXT blocks.

RULES:
1. Use ONLY facts present in the CONTEXT. Never invent facts, numbers, or findings.
2. Each question must be answerable from one or more context blocks; cite the strongest
   support inside the explanation as [Doc: <title>, Page: <N>].
3. Distractors (wrong options) must be plausible but clearly unsupported by the context.
4. Respond with ONLY a JSON array, no prose before or after. Each element:
   {"question": str, "options": [str, str, str, str], "correct_index": 0-3,
    "explanation": str}
5. Exactly 4 options per question; correct_index points at the factually correct option.
6. Difficulty calibration:
   - easy: identify the core finding or conclusion.
   - medium: understand methodology or relationships between findings.
   - hard: precise numbers, trade-offs, constraints.
   - research_level: methodological soundness, causal claims, reproducibility critique.
"""

FLASHCARD_SYSTEM_PROMPT = """You are ScholarEdge, a private on-device study-card generator.
Create active-recall flashcards grounded STRICTLY in the CONTEXT blocks.

RULES:
1. Use ONLY facts present in the CONTEXT.
2. Each card: front is a question prompting recall of ONE specific fact; back is the
   concise answer with its citation [Doc: <title>, Page: <N>].
3. Respond with ONLY a JSON array, no prose before or after. Each element:
   {"front": str, "back": str}
"""


class LearningService:
    def __init__(self, db: AsyncSession, llm: LLMProvider | None = None):
        self.db = db
        self.retrieval_service = RetrievalService(db)
        self.llm_provider = llm or get_llm_provider()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_grounded(sources: list[SourceReference]) -> list[SourceReference]:
        """Keep only chunks strong enough to serve as LLM grounding material."""
        return [s for s in sources if s.relevance_score >= MIN_GROUNDING_SCORE]

    def _llm_is_generative(self) -> bool:
        """True when the configured provider can genuinely write new text.

        The development provider is a deterministic template synthesizer that
        ignores custom system prompts, so learning content falls back to its own
        templates instead of double-templating through it.
        """
        return "development" not in self.llm_provider.name.lower()

    async def _generate(self, prompt: str, system_prompt: str):
        """Call the LLM, returning None on any provider failure."""
        try:
            return await self.llm_provider.generate(prompt, system_prompt=system_prompt)
        except Exception as e:  # noqa: BLE001 - fall back to templates on any failure
            logger.warning("Learning LLM generation failed, falling back to templates: %s", e)
            return None

    @staticmethod
    def _parse_json_array(text: str) -> list[dict] | None:
        """Extract a JSON array from LLM output; returns None on any failure."""
        if not text:
            return None
        candidate = text.strip()
        # Tolerate markdown fences around the JSON payload.
        fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", candidate, re.DOTALL)
        if fence:
            candidate = fence.group(1)
        else:
            start, end = candidate.find("["), candidate.rfind("]")
            if start == -1 or end <= start:
                return None
            candidate = candidate[start : end + 1]
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, list) else None

    @staticmethod
    def _valid_citation(text: str, sources: list[SourceReference]) -> bool:
        """A generated item is grounded only if it cites at least one real source."""
        return any(
            src.document_title in text and str(src.page_number) in text for src in sources
        )

    # ------------------------------------------------------------------
    # Concept explanation
    # ------------------------------------------------------------------

    async def explain_concept(
        self,
        concept: str,
        document_ids: list[str] | None = None,
        level: str = "beginner",
    ) -> ExplainResponse:
        """Explains a technical concept at a selected pedagogical depth."""
        search_res = await self.retrieval_service.search(
            query=concept,
            top_k=4,
            document_ids=document_ids,
            min_score=0.01,
        )

        sources = search_res.results
        if not sources:
            return ExplainResponse(
                concept=concept,
                level=level,
                explanation=f"No indexed material was found in your library discussing '{concept}'. Upload relevant research documents to generate a source-grounded explanation.",
                key_takeaways=[],
                sources=[],
            )

        grounded_sources = self._filter_grounded(sources)

        if grounded_sources and self._llm_is_generative():
            llm_response = await self._explain_with_llm(concept, level, grounded_sources)
            if llm_response is not None:
                return llm_response

        return self._explain_from_template(concept, level, sources)

    async def _explain_with_llm(
        self, concept: str, level: str, sources: list[SourceReference]
    ) -> ExplainResponse | None:
        context_block = build_context_block(sources)
        prompt = (
            f"### CONTEXT:\n{context_block}\n\n"
            f"### CONCEPT:\n{concept}\n\n"
            f"### STYLE:\n{LEVEL_STYLE.get(level, LEVEL_STYLE['beginner'])}"
        )
        gen = await self._generate(prompt, EXPLAIN_SYSTEM_PROMPT)
        if gen is None or "Insufficient evidence" in gen.text:
            return None

        explanation, takeaways = self._split_explanation(gen.text)
        if not self._valid_citation(explanation, sources):
            # LLM answered but ignored citations -> not verifiable, fall back.
            return None

        return ExplainResponse(
            concept=concept,
            level=level,
            explanation=explanation,
            key_takeaways=takeaways,
            sources=sources[:3],
        )

    @staticmethod
    def _split_explanation(text: str) -> tuple[str, list[str]]:
        marker = "KEY TAKEAWAYS:"
        if marker in text:
            body, _, tail = text.partition(marker)
            takeaways = [
                line.lstrip("- ").strip()
                for line in tail.strip().splitlines()
                if line.strip().startswith("-")
            ]
            return body.strip(), takeaways
        return text.strip(), []

    def _explain_from_template(
        self, concept: str, level: str, sources: list[SourceReference]
    ) -> ExplainResponse:
        top_source = sources[0]
        excerpt_clean = top_source.excerpt.replace("\n", " ").strip()
        sentences = [s.strip() for s in excerpt_clean.split(". ") if len(s.strip()) > 10]
        core_point = sentences[0] if sentences else excerpt_clean

        headings = {
            "beginner": f"### Explanation: {concept}",
            "intermediate": f"### Technical Overview: {concept}",
            "deep_dive": f"### Architectural Analysis & Evidence Review: {concept}",
        }
        source_label = f"[Doc: {top_source.document_title}, Page: {top_source.page_number}]"
        body = f"{headings[level]}\n\n{excerpt_clean}\n\n{source_label}"
        takeaways = [
            f"Evidence: {core_point}",
            f"Source: {top_source.document_title}, Page {top_source.page_number}.",
        ]

        return ExplainResponse(
            concept=concept,
            level=level,
            explanation=body,
            key_takeaways=takeaways,
            sources=sources[:3],
        )

    # ------------------------------------------------------------------
    # Quiz generation
    # ------------------------------------------------------------------

    async def generate_quiz(
        self,
        document_ids: list[str] | None = None,
        question_count: int = 4,
        difficulty: str = "medium",
    ) -> QuizResponse:
        """Generates multiple-choice quiz questions grounded in indexed documents."""
        # Retrieve diverse chunks
        queries = ["methodology architecture", "results latency performance", "verification citation", "conclusion finding"]
        collected_sources = []
        for q in queries:
            res = await self.retrieval_service.search(query=q, top_k=2, document_ids=document_ids, min_score=0.01)
            collected_sources.extend(res.results)

        # Deduplicate sources by chunk_id
        unique_sources = []
        seen = set()
        for s in collected_sources:
            if s.chunk_id not in seen:
                seen.add(s.chunk_id)
                unique_sources.append(s)

        target_sources = unique_sources[: max(question_count, 2)]
        grounded_sources = self._filter_grounded(target_sources)

        if grounded_sources and self._llm_is_generative():
            llm_quiz = await self._generate_quiz_with_llm(
                grounded_sources, question_count, difficulty
            )
            if llm_quiz is not None:
                return llm_quiz

        return self._generate_quiz_from_template(unique_sources, question_count, difficulty)

    async def _generate_quiz_with_llm(
        self,
        sources: list[SourceReference],
        question_count: int,
        difficulty: str,
    ) -> QuizResponse | None:
        context_block = build_context_block(sources)
        prompt = (
            f"### CONTEXT:\n{context_block}\n\n"
            f"### TASK:\nGenerate exactly {question_count} quiz question(s) "
            f"at '{difficulty}' difficulty from the context above. "
            "Respond with ONLY the JSON array."
        )
        gen = await self._generate(prompt, QUIZ_SYSTEM_PROMPT)
        if gen is None:
            return None

        items = self._parse_json_array(gen.text)
        if not items:
            return None

        questions: list[QuizQuestion] = []
        for item in items[:question_count]:
            if not isinstance(item, dict):
                continue
            q_text = str(item.get("question", "")).strip()
            options = item.get("options")
            correct_idx = item.get("correct_index")
            explanation = str(item.get("explanation", "")).strip()

            if (
                not q_text
                or not isinstance(options, list)
                or len(options) != 4
                or not all(isinstance(o, str) and o.strip() for o in options)
                or not isinstance(correct_idx, int)
                or not 0 <= correct_idx <= 3
                or not explanation
            ):
                continue

            if not self._valid_citation(explanation, sources):
                continue

            questions.append(
                QuizQuestion(
                    id=str(uuid.uuid4())[:8],
                    question=q_text,
                    options=[o.strip() for o in options],
                    correct_answer_index=correct_idx,
                    correct_answer=options[correct_idx].strip(),
                    explanation=explanation,
                    difficulty=difficulty,
                    source=sources[0],
                )
            )

        if not questions:
            return None

        difficulty_labels = {
            "easy": "Fundamental Understanding",
            "medium": "Methodological Assessment",
            "hard": "Quantitative & Constraint Analysis",
            "research_level": "Deep Architectural & Causal Inference",
        }
        diff_title = difficulty_labels.get(difficulty, difficulty.title())

        return QuizResponse(
            quiz_title=f"ScholarEdge Formative Assessment — {diff_title}",
            difficulty=difficulty,
            questions=questions,
            sources_used=sources,
        )

    def _generate_quiz_from_template(
        self,
        unique_sources: list[SourceReference],
        question_count: int,
        difficulty: str,
    ) -> QuizResponse:
        questions: list[QuizQuestion] = []
        target_sources = unique_sources[:question_count]

        difficulty_labels = {
            "easy": "Fundamental Understanding",
            "medium": "Methodological Assessment",
            "hard": "Quantitative & Constraint Analysis",
            "research_level": "Deep Architectural & Causal Inference",
        }

        for idx, src in enumerate(target_sources):
            sentences = [s.strip() for s in src.excerpt.split(". ") if len(s.strip()) > 15]
            main_sentence = sentences[0] if sentences else src.excerpt[:120]
            if not main_sentence.endswith("."):
                main_sentence += "."

            # Synthesize question style depending on difficulty
            if difficulty == "easy":
                q_text = f"Based on '{src.document_title}' (Page {src.page_number}), what core conclusion or finding is reported?"
                distractors = [
                    "The study concluded that local processing is infeasible for scientific workflows.",
                    "The researchers found that ungrounded speculation produces more reliable answers than cited evidence.",
                    "The authors recommended transmitting all sensitive records to public third-party endpoints.",
                ]
            elif difficulty == "hard":
                q_text = f"Evaluating '{src.document_title}' (Page {src.page_number}), which precise trade-off or constraint is established regarding {src.section or 'the architecture'}?"
                distractors = [
                    "Throughput was doubled by bypassing all memory cache structures without penalty.",
                    "Latency scaled exponentially with document page count due to quadratic vector indexing.",
                    "Accuracy was found to be independent of quantization and weight representation.",
                ]
            elif difficulty == "research_level":
                q_text = f"From a peer-review and reproducibility perspective ('{src.document_title}', Page {src.page_number}), which architectural premise is critically substantiated?"
                distractors = [
                    "Local-first edge copilot architectures fail to satisfy clinical privacy compliance requirements.",
                    "Zero-cloud execution requires proprietary cloud orchestrators during initialization.",
                    "Heuristic aspect-ratio rules provide superior semantic accuracy compared to neural vision models.",
                ]
            else:  # medium
                q_text = f"According to '{src.document_title}' (Page {src.page_number}), which of the following statements is true regarding {src.section or 'the research'}?"
                distractors = [
                    "It mandates transmitting raw user files to an external third-party cloud for validation.",
                    "It demonstrates that citation tracking introduces unmanageable computational overhead without benefits.",
                    "It concludes that on-device architectures cannot operate under strict local memory constraints.",
                ]

            correct_opt = main_sentence
            options = [correct_opt] + distractors
            random.seed(idx + len(src.chunk_id) + len(difficulty))
            random.shuffle(options)
            correct_idx = options.index(correct_opt)

            sec_tag = f" (Section: {src.section})" if src.section else ""
            explanation = (
                f"Grounded directly in {src.document_title}, Page {src.page_number}{sec_tag}: "
                f"\"{main_sentence}\""
            )

            questions.append(
                QuizQuestion(
                    id=str(uuid.uuid4())[:8],
                    question=q_text,
                    options=options,
                    correct_answer_index=correct_idx,
                    correct_answer=correct_opt,
                    explanation=explanation,
                    difficulty=difficulty,
                    source=src,
                )
            )

        diff_title = difficulty_labels.get(difficulty, difficulty.title())
        return QuizResponse(
            quiz_title=f"ScholarEdge Formative Assessment — {diff_title}",
            difficulty=difficulty,
            questions=questions,
            sources_used=target_sources,
        )

    # ------------------------------------------------------------------
    # Flashcards
    # ------------------------------------------------------------------

    async def generate_flashcards(
        self,
        document_ids: list[str] | None = None,
        count: int = 4,
    ) -> FlashcardsResponse:
        """Generates active-recall flashcards from indexed material."""
        # Use a query that matches methodology/findings content well
        search_res = await self.retrieval_service.search(
            query="methodology",
            top_k=count,
            document_ids=document_ids,
            min_score=0.01,
        )

        sources = search_res.results[:count]
        grounded_sources = self._filter_grounded(sources)

        if grounded_sources and self._llm_is_generative():
            llm_cards = await self._generate_flashcards_with_llm(grounded_sources, count)
            if llm_cards is not None:
                return llm_cards

        return self._generate_flashcards_from_template(sources)

    async def _generate_flashcards_with_llm(
        self, sources: list[SourceReference], count: int
    ) -> FlashcardsResponse | None:
        context_block = build_context_block(sources)
        prompt = (
            f"### CONTEXT:\n{context_block}\n\n"
            f"### TASK:\nGenerate exactly {count} flashcard(s) from the context above. "
            "Respond with ONLY the JSON array."
        )
        gen = await self._generate(prompt, FLASHCARD_SYSTEM_PROMPT)
        if gen is None:
            return None

        items = self._parse_json_array(gen.text)
        if not items:
            return None

        flashcards: list[Flashcard] = []
        for item in items[:count]:
            if not isinstance(item, dict):
                continue
            front = str(item.get("front", "")).strip()
            back = str(item.get("back", "")).strip()
            if not front or not back or not self._valid_citation(back, sources):
                continue

            flashcards.append(
                Flashcard(
                    id=str(uuid.uuid4())[:8],
                    front_prompt=front,
                    back_answer=back,
                    source_hint=f"{sources[0].document_title}, Page {sources[0].page_number}",
                )
            )

        if not flashcards:
            return None

        return FlashcardsResponse(flashcards=flashcards)

    def _generate_flashcards_from_template(self, sources: list[SourceReference]) -> FlashcardsResponse:
        flashcards: list[Flashcard] = []
        for src in sources:
            sentences = [s.strip() for s in src.excerpt.split(". ") if len(s.strip()) > 15]
            fact = sentences[0] if sentences else src.excerpt[:120]

            front = f"What is the key insight regarding {src.section or 'the findings'} in \"{src.document_title}\"?"
            back = fact
            hint = f"{src.document_title}, Page {src.page_number}"

            flashcards.append(
                Flashcard(
                    id=str(uuid.uuid4())[:8],
                    front_prompt=front,
                    back_answer=back,
                    source_hint=hint,
                )
            )

        return FlashcardsResponse(flashcards=flashcards)
