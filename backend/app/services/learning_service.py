import random
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.learning import (
    ExplainResponse,
    Flashcard,
    FlashcardsResponse,
    QuizQuestion,
    QuizResponse,
)
from app.services.retrieval_service import RetrievalService


class LearningService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.retrieval_service = RetrievalService(db)

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

        questions: list[QuizQuestion] = []
        target_sources = unique_sources[:question_count]

        for idx, src in enumerate(target_sources):
            sentences = [s.strip() for s in src.excerpt.split(". ") if len(s.strip()) > 15]
            main_sentence = sentences[0] if sentences else src.excerpt[:120]
            if not main_sentence.endswith("."):
                main_sentence += "."

            # Synthesize question based on text
            q_text = f"According to {src.document_title} (Page {src.page_number}), which of the following statements is true regarding {src.section or 'the research'}?"
            correct_opt = main_sentence

            distractors = [
                "It mandates transmitting raw user files to an external third-party cloud for validation.",
                "It demonstrates that citation tracking introduces unmanageable computational overhead without benefits.",
                "It concludes that on-device architectures cannot operate under strict local memory constraints.",
            ]

            options = [correct_opt] + distractors
            random.seed(idx + len(src.chunk_id))
            random.shuffle(options)
            correct_idx = options.index(correct_opt)

            questions.append(
                QuizQuestion(
                    id=str(uuid.uuid4())[:8],
                    question=q_text,
                    options=options,
                    correct_answer_index=correct_idx,
                    explanation=f"Grounded directly in {src.document_title} (Page {src.page_number}): \"{main_sentence}\"",
                    source=src,
                )
            )

        return QuizResponse(
            quiz_title=f"ScholarEdge Formative Assessment ({difficulty.title()} Difficulty)",
            difficulty=difficulty,
            questions=questions,
            sources_used=target_sources,
        )

    async def generate_flashcards(
        self,
        document_ids: list[str] | None = None,
        count: int = 4,
    ) -> FlashcardsResponse:
        """Generates active-recall flashcards from indexed material."""
        search_res = await self.retrieval_service.search(
            query="methodology results conclusion",
            top_k=count,
            document_ids=document_ids,
            min_score=0.01,
        )

        flashcards: list[Flashcard] = []
        for src in search_res.results[:count]:
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
