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

## Results

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
The code defaults stay on the development hash embeddings + hybrid so CI and machines without the
downloaded model still work. With hash embeddings, hybrid is clearly better (72.2% vs 44.4%).

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

1. **The remaining book failure is multi-hop** (B14: Chapter 3 tree induction vs Chapter 11 expected value).
   Top-5 covers one side (page recall 0.2) and Qwen correctly refuses. Candidate levers: larger top-k
   for comparison questions, or per-sub-question retrieval.
   Separately, the bundled `models/qualcomm/all-MiniLM-L6-v2/model.onnx` is **not** MiniLM:
   `scripts/setup_qualcomm_onnx_models.py` builds a single random-weight `Gather` node (P2 work).
2. **Partial refusals:** `RetrievalService.chat` drops all sources when the answer contains
   "Insufficient evidence" anywhere. That hides legitimate cited partial answers (demo Q04), but it also
   hides answers with ungrounded content: in book B11, Qwen listed the CRISP-DM stages from training
   data, then refused. Decide a policy (e.g. keep sources and flag `partial`) before changing it.
3. **The score threshold is a poor abstention signal with hash embeddings.** Unanswerable top-1 scores
   overlap answerable ones, and it causes demo Q09's refusal. With MiniLM the book separates cleanly
   (answerable top-1 ≥ 0.498, unanswerable ≤ 0.401), but that rests on two unanswerable questions.
   Qwen abstained correctly on every unanswerable question in every run, but four questions are too
   few to justify removing or retuning the gate. Add more unanswerable questions first.
4. **Math glyphs are lost at extraction.** pypdf emits only half of each surrogate pair for math italic
   symbols, so formulas become `p(� | �)`. Fixing that needs a different extractor.
5. The academic section-header regex mislabels book chunks (e.g. "Results" on p54).
