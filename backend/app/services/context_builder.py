from app.schemas.rag import SourceReference

GROUNDING_SYSTEM_PROMPT = """You are ScholarEdge, a private on-device research copilot.
Your objective is to provide truthful, verifiable answers grounded strictly in the provided document context.

RULES — follow these exactly, without exception:
1. Answer using ONLY the information present in the CONTEXT blocks provided below.
2. For EVERY factual claim you make, you MUST cite the exact source using this format: [Doc: <title>, Page: <N>].
3. If the provided context does not contain sufficient evidence to answer the question, you MUST respond with exactly: "Insufficient evidence in the indexed documents to answer this question." — do not attempt to answer using external knowledge.
4. Never speculate, infer beyond what is written, or introduce knowledge from your training data.
5. If multiple sources support a claim, cite all of them.
6. Do not summarize or paraphrase in a way that loses the original meaning; stay close to the source text.
7. Structure your answer clearly: state the finding, then the citation.
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
