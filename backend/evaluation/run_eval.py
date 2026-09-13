#!/usr/bin/env python3
"""
ScholarEdge RAG Evaluation Script

Runs the evaluation dataset through the ScholarEdge pipeline and computes:
- Retrieval accuracy
- Groundedness
- Citation accuracy
- Page accuracy
- Abstention accuracy
- Latency metrics
- Token usage
"""

import asyncio
import json
import time
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import async_session_factory
from app.services.retrieval_service import RetrievalService
from app.providers.factory import get_embedding_provider, get_llm_provider


@dataclass
class EvalResult:
    question_id: str
    category: str
    question: str
    expected_answer: str
    expected_sources: list[dict]
    actual_answer: str
    actual_sources: list[dict]
    retrieved_chunks: list[dict]
    has_sufficient_evidence: bool
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    retrieval_accuracy: bool
    groundedness: bool
    citation_accuracy: bool
    page_accuracy: bool
    abstention_accuracy: bool


def load_eval_dataset(path: Path) -> list[dict]:
    with open(path, 'r') as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return text.lower().strip()


def doc_title_match(expected: str, actual: str) -> bool:
    """Check if document titles match (fuzzy)."""
    exp = expected.lower()
    act = actual.lower()
    # Check if key words overlap
    exp_words = set(exp.split())
    act_words = set(act.split())
    # Remove common words
    stop_words = {'the', 'and', 'for', 'on', 'in', 'of', 'a', 'to', 'with', 'by', 'or', 'as', 'is', 'from'}
    exp_words = exp_words - stop_words
    act_words = act_words - stop_words
    # Check significant overlap
    overlap = len(exp_words & act_words)
    return overlap >= 2 or exp in act or act in exp


def check_retrieval_accuracy(expected_sources: list[dict], actual_sources: list[dict]) -> bool:
    """Check if the expected document and page were retrieved."""
    if not expected_sources:
        return True  # No expected sources means unanswerable question
    
    for exp in expected_sources:
        exp_doc = exp.get('document', '')
        exp_page = exp.get('page')
        
        found = False
        for act in actual_sources:
            act_doc = act.get('document_title', '')
            act_page = act.get('page_number')
            
            if doc_title_match(exp_doc, act_doc):
                if exp_page is None or act_page == exp_page:
                    found = True
                    break
        if not found:
            return False
    return True


def check_groundedness(answer: str, sources: list[dict], expected_answer: str) -> bool:
    """Check if answer is grounded in retrieved sources."""
    if not sources:
        return "insufficient evidence" in answer.lower()
    
    answer_lower = answer.lower()
    expected_lower = expected_answer.lower()
    
    # For unanswerable questions
    if "insufficient evidence" in expected_lower:
        return "insufficient evidence" in answer_lower
    
    # Check if answer cites sources properly
    has_citation = "[doc:" in answer_lower or "[source" in answer_lower
    
    # Check if expected key content appears in answer
    expected_keywords = set(expected_lower.split())
    answer_keywords = set(answer_lower.split())
    overlap = len(expected_keywords & answer_keywords) / max(len(expected_keywords), 1)
    
    return has_citation and overlap > 0.2


def check_citation_accuracy(answer: str, expected_sources: list[dict], actual_sources: list[dict]) -> bool:
    """Check if cited documents match expected sources."""
    if not expected_sources:
        return "insufficient evidence" in answer.lower() or len(actual_sources) == 0
    
    answer_lower = answer.lower()
    
    # Check if answer cites the expected document
    for exp in expected_sources:
        exp_doc = exp.get('document', '')
        if exp_doc:
            exp_lower = exp_doc.lower()
            if exp_lower not in answer_lower:
                # Check if any actual source matches
                found = False
                for act in actual_sources:
                    act_doc = act.get('document_title', '')
                    if doc_title_match(exp_doc, act_doc):
                        found = True
                        break
                if not found:
                    return False
    return True


def check_page_accuracy(answer: str, expected_sources: list[dict], actual_sources: list[dict]) -> bool:
    """Check if cited pages match expected pages."""
    if not expected_sources:
        return True
    
    answer_lower = answer.lower()
    
    for exp in expected_sources:
        exp_page = exp.get('page')
        exp_doc = exp.get('document', '')
        
        if exp_page is None:
            continue
            
        # Check if the page is mentioned in the answer for this document
        page_mentioned = f"page {exp_page}" in answer_lower or f"page: {exp_page}" in answer_lower
        
        # Also check actual sources
        found_in_sources = False
        for act in actual_sources:
            act_doc = act.get('document_title', '')
            act_page = act.get('page_number')
            if doc_title_match(exp_doc, act_doc) and act_page == exp_page:
                found_in_sources = True
                break
        
        if not (page_mentioned or found_in_sources):
            return False
    return True


def check_abstention_accuracy(expected_answer: str, actual_answer: str, has_sufficient_evidence: bool) -> bool:
    """Check if the system correctly refuses unanswerable questions."""
    expected_lower = expected_answer.lower()
    actual_lower = actual_answer.lower()
    
    expected_refusal = "insufficient evidence" in expected_lower
    actual_refusal = "insufficient evidence" in actual_lower or not has_sufficient_evidence
    
    return expected_refusal == actual_refusal


async def run_evaluation():
    # Load dataset
    eval_path = Path(__file__).parent / "rag_eval.json"
    dataset = load_eval_dataset(eval_path)
    
    # Initialize services
    async with async_session_factory() as db:
        embedding_provider = get_embedding_provider()
        llm_provider = get_llm_provider()
        retrieval_service = RetrievalService(db, embedding_provider, llm_provider)
        
        results = []
        total_latency = 0
        latencies = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
        print(f"Running evaluation on {len(dataset)} questions...")
        print("=" * 60)
        
        for item in dataset:
            qid = item['id']
            question = item['question']
            expected_answer = item['expected_answer']
            expected_sources = item['expected_sources']
            category = item['category']
            
            print(f"\n{qid} ({category}): {question[:60]}...")
            
            # Run the query
            start_time = time.perf_counter()
            chat_response = await retrieval_service.chat(
                question=question,
                top_k=5,
                min_score_threshold=0.08
            )
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            total_latency += latency_ms
            latencies.append(latency_ms)
            
            # Capture token usage from LLM provider if available
            prompt_tokens = getattr(chat_response, 'prompt_tokens', 0)
            completion_tokens = getattr(chat_response, 'completion_tokens', 0)
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            
            # Extract actual sources
            actual_sources = []
            for src in chat_response.sources:
                actual_sources.append({
                    'document_title': src.document_title,
                    'page_number': src.page_number,
                    'chunk_id': src.chunk_id,
                    'relevance_score': src.relevance_score,
                    'excerpt': src.excerpt[:200] if src.excerpt else ''
                })
            
            # Extract retrieved chunks (full)
            retrieved_chunks = []
            for src in chat_response.sources:
                retrieved_chunks.append({
                    'document_title': src.document_title,
                    'page_number': src.page_number,
                    'chunk_id': src.chunk_id,
                    'relevance_score': src.relevance_score,
                    'excerpt': src.excerpt
                })
            
            # Score metrics
            retrieval_acc = check_retrieval_accuracy(expected_sources, actual_sources)
            grounded = check_groundedness(chat_response.answer, actual_sources, expected_answer)
            citation_acc = check_citation_accuracy(chat_response.answer, expected_sources, actual_sources)
            page_acc = check_page_accuracy(chat_response.answer, expected_sources, actual_sources)
            abstention_acc = check_abstention_accuracy(expected_answer, chat_response.answer, chat_response.has_sufficient_evidence)
            
            result = EvalResult(
                question_id=qid,
                category=category,
                question=question,
                expected_answer=expected_answer,
                expected_sources=expected_sources,
                actual_answer=chat_response.answer,
                actual_sources=actual_sources,
                retrieved_chunks=retrieved_chunks,
                has_sufficient_evidence=chat_response.has_sufficient_evidence,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                retrieval_accuracy=retrieval_acc,
                groundedness=grounded,
                citation_accuracy=citation_acc,
                page_accuracy=page_acc,
                abstention_accuracy=abstention_acc
            )
            
            results.append(result)
            
            # Print status
            status_icons = {
                True: "[OK]",
                False: "[FAIL]"
            }
            print(f"  Retrieval: {status_icons[retrieval_acc]} | Grounded: {status_icons[grounded]} | Citation: {status_icons[citation_acc]} | Page: {status_icons[page_acc]} | Abstention: {status_icons[abstention_acc]} | Latency: {latency_ms:.0f}ms")
        
        # Calculate summary metrics
        total = len(results)
        retrieval_acc_count = sum(1 for r in results if r.retrieval_accuracy)
        grounded_count = sum(1 for r in results if r.groundedness)
        citation_acc_count = sum(1 for r in results if r.citation_accuracy)
        page_acc_count = sum(1 for r in results if r.page_accuracy)
        abstention_acc_count = sum(1 for r in results if r.abstention_accuracy)
        
        # Answerable questions (those with expected sources)
        answerable = [r for r in results if r.expected_sources]
        unanswerable = [r for r in results if not r.expected_sources]
        
        # Metrics calculated on appropriate subsets
        retrieval_acc_pct = retrieval_acc_count / total * 100
        grounded_pct = sum(1 for r in answerable if r.groundedness) / len(answerable) * 100 if answerable else 100
        citation_acc_pct = citation_acc_count / total * 100
        page_acc_pct = page_acc_count / total * 100
        abstention_acc_pct = sum(1 for r in unanswerable if r.abstention_accuracy) / len(unanswerable) * 100 if unanswerable else 100
        
        avg_latency = total_latency / total
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        # Print summary
        print("\n" + "=" * 60)
        print("ScholarEdge RAG Evaluation Summary")
        print("=" * 60)
        print(f"Questions:              {total}")
        print(f"Retrieval accuracy:     {retrieval_acc_pct:.1f}%")
        print(f"Groundedness:           {grounded_pct:.1f}%")
        print(f"Citation accuracy:      {citation_acc_pct:.1f}%")
        print(f"Page accuracy:          {page_acc_pct:.1f}%")
        print(f"Abstention accuracy:    {abstention_acc_pct:.1f}%")
        print(f"\nAverage latency:        {avg_latency:.2f}ms")
        print(f"P95 latency:            {p95_latency:.2f}ms")
        print(f"Total prompt tokens:    {total_prompt_tokens}")
        print(f"Total completion tokens: {total_completion_tokens}")
        
        # Failed questions
        print("\nFAILED:")
        for r in results:
            failures = []
            if not r.retrieval_accuracy:
                failures.append("retrieval")
            if not r.groundedness:
                failures.append("groundedness")
            if not r.citation_accuracy:
                failures.append("citation")
            if not r.page_accuracy:
                failures.append("page citation")
            if not r.abstention_accuracy:
                failures.append("abstention")
            if failures:
                print(f"  {r.question_id} - {', '.join(failures)}")
        
        # Save detailed results
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = results_dir / f"eval_{timestamp}.json"
        
        output_data = {
            "timestamp": timestamp,
            "summary": {
                "total_questions": total,
                "retrieval_accuracy": retrieval_acc_pct,
                "groundedness": grounded_pct,
                "citation_accuracy": citation_acc_pct,
                "page_accuracy": page_acc_pct,
                "abstention_accuracy": abstention_acc_pct,
                "avg_latency_ms": avg_latency,
                "p95_latency_ms": p95_latency,
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens
            },
            "results": [asdict(r) for r in results]
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        # Also save as latest.json
        latest_file = results_dir / "latest.json"
        with open(latest_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nDetailed results saved to: {output_file}")
        print(f"Latest results saved to: {latest_file}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())