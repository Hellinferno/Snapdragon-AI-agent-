#!/usr/bin/env python3
"""ScholarEdge RAG evaluation runner.

Builds a fresh, isolated index of a dataset's corpus, then scores the pipeline with the
pure metrics in evaluation/metrics.py.

    # Retrieval only: deterministic, no LLM calls, no API cost
    python -m evaluation.run_eval --dataset data_science_for_business --corpus-dir .. --mode retrieval

    # Retrieval + generation + citations through the configured LLM provider
    python -m evaluation.run_eval --dataset data_science_for_business --corpus-dir .. --mode full --label baseline

Run from the backend/ directory. Results go to evaluation/results/<dataset>/<label>.json.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.providers.factory import (  # noqa: E402
    describe_embedding_provider,
    effective_hybrid_retrieval,
    get_embedding_provider,
    get_llm_provider,
    retrieval_mode,
)
from app.services.document_service import DocumentService  # noqa: E402
from app.services.retrieval_service import RetrievalService  # noqa: E402
from evaluation.metrics import (  # noqa: E402
    GenerationSummary,
    Ratio,
    RetrievalSummary,
    judge_generation,
    judge_retrieval,
    percentile,
    validate_question,
)

EVAL_DIR = Path(__file__).resolve().parent
DATASETS_DIR = EVAL_DIR / "datasets"
RESULTS_DIR = EVAL_DIR / "results"
CACHE_DIR = EVAL_DIR / ".cache"
EXCERPT_CHARS = 160  # the repository is public: keep copyrighted corpus text in results short
DEFAULT_CORPUS_DIRS = {"demo_papers": BACKEND_DIR / "data" / "demo_papers"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=BACKEND_DIR, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return ""

    return {"commit": run("rev-parse", "--short", "HEAD") or None, "dirty": bool(run("status", "--porcelain", "--", "app", "evaluation"))}


def load_dataset(name_or_path: str) -> tuple[dict, Path]:
    path = Path(name_or_path)
    if not path.suffix:
        path = DATASETS_DIR / f"{name_or_path}.json"
    dataset = json.loads(path.read_text(encoding="utf-8"))
    ids = [q["id"] for q in dataset["questions"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate question ids in dataset")
    for question in dataset["questions"]:
        validate_question(question)
    return dataset, path


def resolve_corpus(dataset: dict, corpus_dir: Path | None) -> list[tuple[dict, Path]]:
    base = corpus_dir or DEFAULT_CORPUS_DIRS.get(dataset["name"])
    if base is None:
        raise SystemExit(f"Dataset '{dataset['name']}' needs --corpus-dir pointing at its PDFs")
    resolved = []
    for entry in dataset["corpus"]:
        pdf = Path(base) / entry["filename"]
        if not pdf.exists():
            raise SystemExit(f"Corpus file not found: {pdf}")
        if entry.get("sha256") and sha256_file(pdf) != entry["sha256"]:
            raise SystemExit(f"{pdf.name} does not match the dataset's sha256; page labels would be wrong")
        resolved.append((entry, pdf))
    return resolved


def excerpt(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= EXCERPT_CHARS else flat[: EXCERPT_CHARS - 1] + "…"


def source_dict(src) -> dict:
    return {
        "document_title": src.document_title,
        "page_number": src.page_number,
        "chunk_id": src.chunk_id,
        "score": src.relevance_score,
        "text": src.excerpt,
    }


async def build_index(session: AsyncSession, corpus: list[tuple[dict, Path]], embedding) -> None:
    service = DocumentService(session, embedding)
    for entry, pdf in corpus:
        t0 = time.perf_counter()
        result = await service.process_local_pdf(pdf, title=entry["title"])
        print(f"Indexed {entry['title']!r}: {result.status} in {time.perf_counter() - t0:.1f}s")


def summarize_latencies(values: list[float]) -> dict:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "mean_ms": round(sum(values) / len(values), 1),
        "p50_ms": round(percentile(values, 50), 1),
        "p95_ms": round(percentile(values, 95), 1),
    }


async def evaluate(args: argparse.Namespace) -> dict:
    dataset, dataset_path = load_dataset(args.dataset)
    corpus = resolve_corpus(dataset, args.corpus_dir)
    questions = [q for q in dataset["questions"] if not args.only or q["id"] in args.only]

    # Isolated storage: never touches the app database or its uploads
    work_dir = CACHE_DIR / dataset["name"]
    shutil.rmtree(work_dir, ignore_errors=True)
    (work_dir / "uploads").mkdir(parents=True)
    settings.UPLOAD_DIR = work_dir / "uploads"
    engine = create_async_engine(f"sqlite+aiosqlite:///{work_dir / 'eval.db'}", connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    # An explicit --embedding-provider / --hybrid wins; otherwise the same resolution the
    # application uses, so a default-mode run measures the default configuration.
    requested_embedding = None if args.embedding_provider == "auto" else args.embedding_provider
    embedding = get_embedding_provider(requested_embedding)
    embedding_status = describe_embedding_provider(embedding)
    if args.hybrid is not None:
        settings.HYBRID_RETRIEVAL = args.hybrid
    hybrid_active = effective_hybrid_retrieval(embedding)
    llm = get_llm_provider() if args.mode == "full" else None

    retrieval = RetrievalSummary()
    generation = GenerationSummary()
    by_category: dict[str, dict[str, Ratio]] = defaultdict(lambda: {"evidence_hit": Ratio(), "page_hit": Ratio(), "correct": Ratio()})
    records: list[dict] = []
    search_latencies: list[float] = []
    chat_latencies: list[float] = []
    top_scores = {"answerable": [], "unanswerable": []}
    tokens = {"prompt": 0, "completion": 0}

    async with session_factory() as session:
        await build_index(session, corpus, embedding)
        service = RetrievalService(session, embedding, llm)

        for q in questions:
            t0 = time.perf_counter()
            # Retrieval is measured without the evidence threshold so it is not confounded with abstention
            search = await service.search(q["question"], top_k=args.top_k, min_score=float("-inf"))
            search_latencies.append((time.perf_counter() - t0) * 1000)
            retrieved = [source_dict(s) for s in search.results]
            top_score = retrieved[0]["score"] if retrieved else None
            top_scores["answerable" if q["answerable"] else "unanswerable"].append(top_score)

            record: dict = {
                "id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "answerable": q["answerable"],
                "expected_sources": q["expected_sources"],
                "retrieved": [
                    {**{k: r[k] for k in ("document_title", "page_number", "score")}, "excerpt": excerpt(r["text"])}
                    for r in retrieved
                ],
            }

            if q["answerable"]:
                rj = judge_retrieval(q, retrieved)
                retrieval.add(rj)
                if rj.evidence_hit is not None:
                    by_category[q["category"]]["evidence_hit"].add(rj.evidence_hit)
                by_category[q["category"]]["page_hit"].add(rj.page_hit)
                record["retrieval"] = {
                    "doc_hit": rj.doc_hit,
                    "page_hit": rj.page_hit,
                    "page_recall": round(rj.page_recall, 4),
                    "evidence_hit": rj.evidence_hit,
                    "first_relevant_rank": rj.first_relevant_rank,
                }

            if llm is not None:
                t0 = time.perf_counter()
                chat = await service.chat(q["question"], top_k=args.top_k, min_score_threshold=args.min_score)
                chat_latencies.append((time.perf_counter() - t0) * 1000)
                tokens["prompt"] += chat.prompt_tokens
                tokens["completion"] += chat.completion_tokens
                context = [source_dict(s) for s in chat.sources]
                gj = judge_generation(q, chat.answer, context)
                generation.add(q, gj)
                if q["answerable"]:
                    by_category[q["category"]]["correct"].add(bool(gj.correct))
                record["generation"] = {
                    "answer": chat.answer,
                    "has_sufficient_evidence": chat.has_sufficient_evidence,
                    "refused": gj.refused,
                    "correct": gj.correct,
                    "grounded": gj.grounded if q["answerable"] and not gj.refused else None,
                    "citations": [{"document": d, "page": p} for d, p in gj.citations],
                    "cited_expected_page": gj.cited_expected_page if q["answerable"] and not gj.refused else None,
                    "context_pages": [c["page_number"] for c in context],
                }
            records.append(record)
            print_question(record)

    await engine.dispose()

    def score_stats(values: list[float | None]) -> dict:
        present = [v for v in values if v is not None]
        return {"min": min(present, default=None), "median": percentile(present, 50), "max": max(present, default=None)}

    gen = generation.to_dict() if llm is not None else None
    return {
        "dataset": dataset["name"],
        "label": args.label,
        "mode": args.mode,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": {
            "git": git_state(),
            "python": platform.python_version(),
            "dataset_sha256": sha256_file(dataset_path),
            "corpus": [{"title": e["title"], "sha256": sha256_file(p)} for e, p in corpus],
            "embedding_provider": embedding.name,
            "embedding_degraded": embedding_status.degraded,
            "embedding_degraded_reason": embedding_status.reason,
            "retrieval_mode": retrieval_mode(embedding),
            "llm_provider": llm.name if llm else None,
            # The value actually used for this run, not the (possibly unset) setting.
            "hybrid_retrieval": hybrid_active,
            "hybrid_retrieval_explicit": args.hybrid is not None,
            "top_k": args.top_k,
            "min_score_threshold": args.min_score if llm else None,
            "chunk_size_chars": settings.CHUNK_SIZE_CHARS,
            "chunk_overlap_chars": settings.CHUNK_OVERLAP_CHARS,
        },
        "counts": {
            "questions": len(questions),
            "answerable": sum(q["answerable"] for q in questions),
            "unanswerable": sum(not q["answerable"] for q in questions),
        },
        "retrieval": retrieval.to_dict(),
        "generation": gen["generation"] if gen else None,
        "citation": gen["citation"] if gen else None,
        "by_category": {
            cat: {k: v.to_dict() for k, v in ratios.items() if v.denominator}
            for cat, ratios in sorted(by_category.items())
        },
        "top1_score": {k: score_stats(v) for k, v in top_scores.items()},
        "latency": {"search": summarize_latencies(search_latencies), "chat": summarize_latencies(chat_latencies)},
        "tokens": tokens if llm else None,
        "results": records,
    }


def fmt(metric: dict | None) -> str:
    if metric is None:
        return "n/a"
    if "percent" in metric:
        p = metric["percent"]
        return f"{'n/a' if p is None else f'{p:5.1f}%'} ({metric['numerator']}/{metric['denominator']})"
    m = metric["mean"]
    return f"{'n/a' if m is None else f'{m:.3f}'} (n={metric['count']})"


def print_question(record: dict) -> None:
    parts = [record["id"], record["category"]]
    if "retrieval" in record:
        r = record["retrieval"]
        parts.append(f"evidence={r['evidence_hit']} page={r['page_hit']} rank={r['first_relevant_rank']}")
    if "generation" in record:
        g = record["generation"]
        parts.append(f"refused={g['refused']} correct={g['correct']} grounded={g['grounded']}")
    print("  " + " | ".join(str(p) for p in parts))


def print_summary(report: dict) -> None:
    config = report["config"]
    print("\n" + "=" * 72)
    print(f"{report['dataset']} [{report['label']}] mode={report['mode']}  "
          f"embedding={config['embedding_provider']}  hybrid={config['hybrid_retrieval']}  "
          f"llm={config['llm_provider']}")
    if config.get("embedding_degraded"):
        print(f"DEGRADED EMBEDDINGS ({config.get('retrieval_mode')}): {config['embedding_degraded_reason']}")
    print("=" * 72)
    for group in ("retrieval", "generation", "citation"):
        if report[group]:
            print(f"{group.upper()}")
            for name, metric in report[group].items():
                print(f"  {name:24s} {fmt(metric)}")
    print("BY CATEGORY")
    for cat, metrics in report["by_category"].items():
        print(f"  {cat:16s} " + "  ".join(f"{k}={fmt(v)}" for k, v in metrics.items()))
    print(f"TOP-1 SCORE  {report['top1_score']}")
    print(f"LATENCY      {report['latency']}")
    if report["tokens"]:
        print(f"TOKENS       {report['tokens']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", default="data_science_for_business", help="dataset name in evaluation/datasets or a path")
    parser.add_argument("--corpus-dir", type=Path, help="directory containing the dataset's corpus PDFs")
    parser.add_argument("--mode", choices=["retrieval", "full"], default="retrieval")
    parser.add_argument(
        "--embedding-provider",
        choices=["auto", "development", "onnx_minilm", "qualcomm"],
        default="auto",
        help="embedding backend; 'auto' follows the application's own resolution",
    )
    hybrid = parser.add_mutually_exclusive_group()
    hybrid.add_argument(
        "--hybrid",
        dest="hybrid",
        action="store_true",
        default=None,
        help="force BM25 fusion on (default: follow the resolved embedding provider)",
    )
    hybrid.add_argument(
        "--no-hybrid",
        dest="hybrid",
        action="store_false",
        help="force vector-only retrieval",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-score", type=float, default=0.08, help="evidence threshold passed to chat() in full mode")
    parser.add_argument("--label", default=None, help="result file name (default: <mode>_<timestamp>)")
    parser.add_argument("--only", nargs="*", help="restrict to these question ids")
    args = parser.parse_args()
    args.label = args.label or f"{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    report = asyncio.run(evaluate(args))
    print_summary(report)

    out = RESULTS_DIR / report["dataset"] / f"{args.label}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {out.relative_to(BACKEND_DIR)}")


if __name__ == "__main__":
    main()
