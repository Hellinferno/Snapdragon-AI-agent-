from typing import Literal
from pydantic import BaseModel, Field

from app.schemas.rag import SourceReference

ExplanationLevel = Literal["beginner", "intermediate", "deep_dive"]
DifficultyLevel = Literal["easy", "medium", "hard"]


class ExplainRequest(BaseModel):
    concept: str = Field(..., min_length=1, description="Scientific or academic concept to explain")
    document_ids: list[str] | None = Field(None, description="Optional filter by document IDs")
    level: ExplanationLevel = Field("beginner", description="Pedagogical depth: beginner, intermediate, deep_dive")


class ExplainResponse(BaseModel):
    concept: str
    level: str
    explanation: str
    key_takeaways: list[str]
    sources: list[SourceReference]


class QuizQuestion(BaseModel):
    id: str
    question: str
    options: list[str]
    correct_answer_index: int
    explanation: str
    source: SourceReference | None = None


class QuizRequest(BaseModel):
    document_ids: list[str] | None = Field(None, description="Optional document IDs to scope the quiz")
    question_count: int = Field(4, ge=1, le=10, description="Number of questions to generate")
    difficulty: DifficultyLevel = Field("medium", description="Quiz difficulty level")


class QuizResponse(BaseModel):
    quiz_title: str
    difficulty: str
    questions: list[QuizQuestion]
    sources_used: list[SourceReference]


class Flashcard(BaseModel):
    id: str
    front_prompt: str
    back_answer: str
    source_hint: str


class FlashcardsResponse(BaseModel):
    flashcards: list[Flashcard]
