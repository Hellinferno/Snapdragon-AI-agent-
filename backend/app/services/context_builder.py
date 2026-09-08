from app.schemas.rag import SourceReference

GROUNDING_SYSTEM_PROMPT = """You are ScholarEdge, a private on-device research copilot.
Your objective is to provide truthful, verifiable answers grounded strictly in the provided document context.

RULES:
1. Answer using ONLY the information provided in the CONTEXT.
2. For every factual claim you make, you MUST cite the source using the exact format: [Doc: <title>, Page: <page>].
3. If the provided context does not contain sufficient evidence to answer the question, you MUST explicitly state: "Insufficient evidence in the indexed documents to answer this question."
4. Never speculate, assume, or introduce external unverified knowledge.
"""


def build_context_block(sources: list[SourceReference]) -> str:
    """Formats a list of retrieved SourceReference objects into a structured context block."""
    if not sources:
        return "NO_RELEVANT_EVIDENCE"

    blocks: list[str] = []
    for idx, src in enumerate(sources, 1):
        sec_info = f", Section: \"{src.section}\"" if src.section else ""
        header = f"[Source {idx}: \"{src.document_title}\", Page {src.page_number}{sec_info}]"
        blocks.append(f"{header}\n{src.excerpt}")

    return "\n\n".join(blocks)


def build_rag_prompt(question: str, context_block: str) -> str:
    """Builds the full user prompt combining context and question."""
    return f"### CONTEXT:\n{context_block}\n\n### QUESTION:\n{question}"
