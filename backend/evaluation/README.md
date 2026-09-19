# ScholarEdge RAG evaluation

Run from `backend/`:

```bash
# Retrieval only: deterministic, no LLM, free. Use this while iterating on retrieval.
python -m evaluation.run_eval --dataset data_science_for_business --corpus-dir .. --mode retrieval

# Retrieval + generation + citations through the configured LLM (reads backend/.env)
python -m evaluation.run_eval --dataset data_science_for_business --corpus-dir .. --mode full --label my_run
```

Each run builds a fresh index in `evaluation/.cache/` (never the app database), verifies the
corpus PDF against the dataset's sha256, and writes `results/<dataset>/<label>.json` with the
config, git commit, per-question judgments and short excerpts.

## Datasets

| Dataset | Corpus | Questions | Purpose |
|---|---|---|---|
| `data_science_for_business` | Provost & Fawcett, *Data Science for Business* (409 pages, ~1,900 chunks) | 18 answerable + 2 unanswerable | **Primary benchmark** |
| `demo_papers` | 3 synthetic 5-page papers in `data/demo_papers` | 13 + 2 | Smoke test. With 15 chunks, top-5 returns a third of the corpus, so its retrieval numbers say little |

The book PDF is copyrighted and is **not** in the repository. Put it anywhere and pass `--corpus-dir`.
Page numbers are PDF page indices (printed page = PDF page − 24 in the main matter).

Every answerable question has `evidence` phrases, each verified to occur on one of its expected
pages. Changes to ground truth are recorded in the dataset's `changelog`.

## Metrics

All rates report `numerator/denominator`. A rate with nothing eligible is `null`, never 100%.

**Retrieval** (answerable questions, top-k, measured *without* the evidence threshold):
`doc_hit_at_k`, `page_hit_at_k`, `evidence_hit_at_k` (a retrieved chunk contains an evidence
phrase: the strictest and primary signal), `page_recall_at_k`, `mrr`.

**Generation:** `answer_correctness` (every keyword group present; a refusal counts as wrong),
`false_refusal_rate` (answerable questions refused), `abstention_accuracy` (unanswerable
questions refused), `groundedness` (non-refused answers with ≥1 citation, all to retrieved pages).

**Citation** (parsed from the answer text only): `citation_rate`, `cited_page_accuracy`,
`cited_doc_accuracy`, `citation_faithfulness` (citations pointing at pages that were in the context).

### Known limitations

- **Groundedness is citation-level, not claim-level.** It proves each citation points at a page the
  model was given. It cannot detect uncited claims or a cited page that doesn't support the claim
  (book B07 cites p137 for a paraphrase that page doesn't state). A claim-level check needs an LLM judge.
- **Refusal = the phrase "insufficient evidence" anywhere in the answer**, matching the app's own logic.
  Partial answers that end with that phrase count as refusals (see findings below).
- **`evidence_hit` is conservative:** a chunk that answers the question but is split away from the
  exact phrase counts as a miss (book B16).
- **20 questions:** one question moves a metric by 5.6 points, so differences of ±1 question are noise.

## Regression guard

The `demo_papers` ranking is frozen by `tests/test_retrieval_regression.py`, which re-indexes the
corpus and fails if MRR or page recall@5 falls below the reference in the committed result files
here. Floors are (reference − 0.03), sized so a single rank-1→rank-2 slip on the 13 answerable
demo questions fails the build. Raising a floor means committing a new result file and updating the
reference in that test.

The demo corpus cannot see `CHUNK_SIZE_CHARS` / `CHUNK_OVERLAP_CHARS` changes at all: each of its
15 pages yields exactly one chunk, so 600 and 1200 chars measure identically. Chunk-size work has
to be measured on the book corpus with the commands above.

## Results

### Frozen RAG baseline (HEAD `1e78440`, 2026-09-15)

Book benchmark, recommended configuration: `EMBEDDING_PROVIDER=onnx_minilm`, `HYBRID_RETRIEVAL=false`,
top-k = 5, chunk 600/100 chars, evidence threshold 0.08, Qwen 2.5 72B Instruct via OpenRouter.
Result files: `results/data_science_for_business/head_retrieval_k*.json` and `head_full_k5.json`.
Dataset v3 (B03 expected pages widened to [38, 51], see changelog).

| Metric | Baseline | Notes |
|---|---:|---|
| Doc hit@5 | 18/18 (100%) | single-document corpus, so trivially satisfied |
| Page hit@5 | 18/18 (100%) | |
| Evidence hit@5 | 17/18 (94.4%) | miss: B06 (see per-question table) |
| Page recall@5 | 0.812 | multi-page questions cap this: B11 0.17, B14 0.20 |
| MRR | 0.681 | first evidence chunk at rank 1 for 10/18, rank <= 3 for 17/18 |
| Answer correctness | 17/18 (94.4%) | miss: B14 |
| False refusal rate | 1/18 (5.6%) | B14 |
| Abstention accuracy | 2/2 (100%) | |
| Groundedness | 17/17 (100%) | citation-level only (see limitations) |
| Citation rate | 17/17 (100%) | |
| Cited page accuracy | 17/17 (100%) | 16/17 before the B03 ground-truth fix |
| Citation faithfulness | 35/35 (100%) | |
| Search P50 / P95 | 603 ms / 695 ms | MiniLM fp32 on CPU + SQLite full vector scan, ~1,900 chunks |
| Generation P50 / P95 | 4,164 ms / 21,470 ms | `chat()` end to end: search + OpenRouter round trip; not an on-device number |
| Tokens (20 questions) | 19,208 prompt / 2,774 completion | |

Retrieval and generation numbers reproduce the `p1b_minilm` run from commit `b717c88` exactly
(same 17/18, 0.812, 0.681), so the pipeline is deterministic across re-indexing.

### Top-k sweep (retrieval mode, MiniLM, HEAD)

| k | hybrid | Evidence hit | Page hit | Page recall | MRR | Search P50 / P95 |
|---|---|---|---|---|---|---|
| 3 | no | 16/18 (88.9%) | 17/18 | 0.773 | 0.667 | 692 / 784 ms |
| **5** | **no** | **17/18 (94.4%)** | **18/18** | **0.812** | **0.681** | 624 / 661 ms |
| 8 | no | 17/18 (94.4%) | 18/18 | 0.840 | 0.681 | 567 / 629 ms |
| 10 | no | 17/18 (94.4%) | 18/18 | 0.868 | 0.681 | 557 / 593 ms |
| 10 | yes | 18/18 (100%) | 18/18 | 0.809 | 0.649 | 555 / 714 ms |

- k=3 loses B14's only Chapter 3 hit (rank 4) and B12 drops to one of four pages.
- k=8 and k=10 change nothing above rank 5 (MRR identical). The extra page recall comes from B08
  (p77 enters at rank 6-10) and B15 (p244 at rank 7); both were already answered correctly at k=5.
- **B14's Chapter 11 pages (305-307) are absent from the vector top-10 entirely.** Hybrid k=10 places
  p306 at rank 8 but costs B07 (rank 1 -> 4) and B15 (rank 1 -> 3). A reranker over the top-10 therefore
  has no failing question to fix in vector-only mode: the missing candidate never reaches the reranker.
- Search latency differences between k values are noise; the SQLite scan dominates regardless of k.
- 29 of the 100 top-5 slots (20 questions x 5) are taken by a second or later chunk from a page already
  in the list (B01: p27 x5, B16: p155 x4, B15: p268 x4, B10: p54 x4). `search()` de-duplicates identical
  text but has no per-page cap, so multi-page questions get fewer distinct pages than k suggests.

### Per-question review of the baseline (full mode, k = 5)

Every answerable question was checked against this taxonomy: (1) PDF parsing, (2) chunking,
(3) embedding, (4) retrieval ranking, (5) insufficient top-k, (6) evidence threshold, (7) LLM generation,
(8) citation generation, (9) evaluation-dataset problem.

| id | category | retrieval | generation | classification |
|---|---|---|---|---|
| B01, B02, B04, B05 | direct_factual | evidence rank 1, 3, 1, 2 | correct, cited expected page | pass |
| B03 | direct_factual | rank 1 = p38, rank 2 = p51 | correct, cited p38 | **was scored as a wrong citation: dataset problem (9).** p38 (Chapter 1) also spells out the acronym. Fixed in dataset v3. |
| B06 | conceptual | page hit (p48 at rank 3), **evidence miss** | correct, cited p48 twice | **chunking (2) plus a conservative metric.** The retrieved p48 chunk starts just after the evidence sentence ("...ferent techniques than unsupervised tasks do"); the neighbouring chunk with the exact phrase is outside the top-10. Not a user-visible failure. |
| B07-B10 | conceptual | evidence rank 1, 1, 2, 2 | correct | pass |
| B11 | multi_page | evidence rank 1; page recall 0.17 (p51 only) | correct: Qwen lists all six stages from the p51 overview chunk | pass; low recall is built into the question (6 expected pages, 5 slots) |
| B12 | multi_page | rank 3; 3 of 4 pages | correct | pass |
| B13 | multi_page | rank 1; both pages | correct | pass |
| B14 | cross_section | p97 at rank 4-5 (Chapter 3 side); **Chapter 11 side never retrieved** (absent from top-10; rank 8 with hybrid) | refused: "Insufficient evidence" | **retrieval ranking failure on a compound query (4).** Not top-k (5): still missing at k=10. Not LLM (7): refusing was right for the context it got. Fix belongs in retrieval: decompose the question into per-chapter sub-queries and merge, or run hybrid with a larger pool for comparison questions. |
| B15 | cross_section | p268 at rank 1, 3, 4, 5; p244 at rank 7 | correct | pass; four slots on one page |
| B16 | cross_section | p155 at rank 1, 3, 4, 5; p137 absent from top-10 | correct (answered from p155/156) | pass; the p137 evidence check is conservative |
| B17, B18 | page_citation | rank 1, 2 | correct page numbers | pass |
| B19, B20 | unanswerable | top-1 score 0.40 / 0.40 vs answerable min 0.498 | refused | pass |

Failure-class totals for the baseline: 1 retrieval ranking (B14), 1 chunking/metric (B06, answer still
correct), 1 dataset problem (B03, fixed). No PDF-parsing, embedding, threshold, LLM or citation failures
on this benchmark. For reference, the non-recommended MiniLM + hybrid run (`p1b_minilm_hybrid`) adds
three more: B07 (BM25 promotes generic p11 chunks over the definition: evidence miss), B13 (LLM omits
"average/variance": generation), B15 (p244 pushed out of the top-5: ranking).

### Earlier runs (commit `b717c88`, dataset v2)

Book, top-k = 5, Qwen 2.5 72B via OpenRouter.

| Metric | `baseline` (hash vectors) | `p1_hybrid` (hash + BM25) | **`p1b_minilm` (MiniLM, vector only)** | `p1b_minilm_hybrid` |
|---|---|---|---|---|
| Evidence hit@5 | 9/18 (50.0%) | 12/18 (66.7%) | **17/18 (94.4%)** | 16/18 (88.9%) |
| Page hit@5 | 12/18 (66.7%) | 17/18 (94.4%) | **18/18 (100%)** | 18/18 (100%) |
| Page recall@5 | 0.493 | 0.729 | **0.812** | 0.784 |
| MRR | 0.431 | 0.509 | **0.681** | 0.630 |
| **Answer correctness** | 8/18 (44.4%) | 13/18 (72.2%) | **17/18 (94.4%)** | 15/18 (83.3%) |
| **False refusal rate** | 8/18 (44.4%) | 1/18 (5.6%) | 1/18 (5.6%) | 1/18 (5.6%) |
| Abstention accuracy | 2/2 | 2/2 | 2/2 | 2/2 |
| Groundedness | 10/10 | 17/17 | 17/17 | 17/17 |
| Cited page accuracy | 10/10 | 15/17 | 16/17 | 16/17 |
| Citation faithfulness | 13/13 | 24/24 | 33/33 | 29/29 |

Demo papers, answer correctness: 4/13 → 6/13 → **12/13** (MiniLM, either mode), false refusals 7/13 → 5/13 → 0/13.

**Recommended configuration:** `EMBEDDING_PROVIDER=onnx_minilm`, `HYBRID_RETRIEVAL=false` (see `.env.example`).

This is also the **shipped default**, because leaving both settings unset resolves to exactly that:
`get_embedding_provider()` selects the ONNX MiniLM model when it is present on disk and falls back to
the deterministic hash embeddings only when it is not, and `retrieval_mode()` follows the resolved
provider — vector-only with semantic embeddings, BM25-fused with the hash fallback (where the
fallback run of this table shows hybrid is clearly the better half of a bad deal: 72.2% vs 44.4%).
Coupling the two is deliberate: the measured combinations are 94.4% (MiniLM, vector-only), 83.3%
(MiniLM, hybrid), 72.2% (hash, hybrid) and 44.4% (hash, vector-only), so no single setting is right
for both providers, and an uncoupled default would land on one of the two middle rows.

A degraded machine therefore stays usable *and* self-reporting: `/api/health` returns
`embedding_provider`, `embedding_degraded` and `retrieval_mode` from the providers that were actually
resolved, so hash-and-hybrid mode is announced rather than mistaken for the 94.4% configuration.
Tests pin the development providers explicitly, so CI never depends on which models are downloaded.

Cost of MiniLM on CPU (fp32 ONNX): indexing the 409-page book takes ~100 s (vs ~13 s for hash vectors).
Search latency is ~550 ms, dominated by the SQLite vector scan rather than the model.

## Retrieval experiment log (book, retrieval mode)

| Variant | Evidence hit | Page hit | Page recall | MRR | Kept? |
|---|---|---|---|---|---|
| Baseline: hash vectors, char-window chunker | 9/18 | 66.7% | 0.493 | 0.431 | — |
| E1: sentence chunker + soft-hyphen rejoin, vectors only | 9/18 | 66.7% | 0.479 | 0.363 | no, no gain alone |
| E2: E1 + hybrid BM25/vector RRF | **13/18** | 88.9% | 0.656 | 0.479 | chunker replaced (see E2b) |
| E3: E2 + demote TOC/index chunks | 13/18 | 88.9% | 0.656 | 0.479 | **reverted**, identical numbers |
| E2b: E2 with chunk-overlap bug fixed | 12/18 | 94.4% | 0.729 | 0.474 | no |
| Ablation: hybrid + original chunker | 12/18 | 94.4% | **0.740** | **0.546** | — |
| P1 final: hybrid + original chunker + soft-hyphen rejoin | 12/18 | 94.4% | 0.729 | 0.509 | yes (hash embeddings) |
| MiniLM (real all-MiniLM-L6-v2), vector only | **17/18** | **100%** | **0.812** | **0.681** | **yes (recommended)** |
| MiniLM + BM25 hybrid | 16/18 | 100% | 0.784 | 0.630 | no, B07 drops out of the top 5 |

Real semantic embeddings are the largest single gain; with them, BM25 fusion costs one retrieval
hit and two correct answers (B07 "define overfitting" drops out of the top 5). With hash embeddings,
hybrid retrieval is the only change with a clear effect. The chunking variants sit within ±1
question of each other, so the existing chunker was kept rather than tuning to 18 questions.
The E2 sentence chunker carried almost no overlap (a bug), which likely inflated its single extra hit.

## Findings for the next iteration

1. **The only failing question is multi-hop retrieval** (B14: Chapter 3 tree induction vs Chapter 11 expected
   value). The top-k sweep shows the Chapter 11 side is not in the vector top-10 at all, so neither a larger k
   nor a reranker over the current candidates fixes it. Candidate levers, in order: (a) query decomposition
   for comparison questions (retrieve per sub-question, merge), (b) hybrid retrieval with a larger pool
   only when the query names several chapters/sections, (c) a per-page cap in `search()` so the 29% of
   slots spent on repeated pages go to distinct pages. Each is one retrieval-mode run to test.
2. **Reranking is not the next move.** With MiniLM the first relevant chunk is at rank <= 3 for 17/18
   questions (MRR 0.681); the two pages a reranker could pull up from ranks 6-10 (B08 p77, B15 p244)
   belong to questions that are already answered correctly.
3. **Search latency is the SQLite vector scan (~550-600 ms), not the model.** An in-memory matrix or an
   ANN index is the lever if search latency matters for the demo; it does not affect quality.
4. **Partial refusals:** `RetrievalService.chat` drops all sources when the answer contains
   "Insufficient evidence" anywhere. That hides legitimate cited partial answers (demo Q04), but it also
   hides answers with ungrounded content: in the hash-embedding book run, Qwen listed the CRISP-DM stages
   from training data, then refused. Decide a policy (e.g. keep sources and flag `partial`) before changing it.
6. **The score threshold is a poor abstention signal with hash embeddings.** With MiniLM the book separates
   cleanly (answerable top-1 >= 0.498, unanswerable <= 0.401), but that rests on two unanswerable questions.
   Qwen abstained correctly on every unanswerable question in every run. Add more unanswerable questions
   before removing or retuning the gate.
7. **Math glyphs are lost at extraction.** pypdf emits only half of each surrogate pair for math italic
   symbols, so formulas become `p(? | ?)`. Fixing that needs a different extractor.
8. The academic section-header regex mislabels book chunks (e.g. "Results" on p54).
