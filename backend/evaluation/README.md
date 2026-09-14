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

Book, top-k = 5, Qwen 2.5 72B via OpenRouter, development hash embeddings.

| Metric | `baseline` | `p1_hybrid` |
|---|---|---|
| Evidence hit@5 | 9/18 (50.0%) | 12/18 (66.7%) |
| Page hit@5 | 12/18 (66.7%) | 17/18 (94.4%) |
| Page recall@5 | 0.493 | 0.729 |
| MRR | 0.431 | 0.509 |
| **Answer correctness** | **8/18 (44.4%)** | **13/18 (72.2%)** |
| **False refusal rate** | **8/18 (44.4%)** | **1/18 (5.6%)** |
| Abstention accuracy | 2/2 | 2/2 |
| Groundedness | 10/10 | 17/17 |
| Cited page accuracy | 10/10 | 15/17 |
| Citation faithfulness | 13/13 | 24/24 |

Demo papers: evidence hit 12/13 → 13/13, MRR 0.718 → 0.872, correctness 4/13 → 6/13, false refusals 7/13 → 5/13.

## Retrieval experiment log (book, retrieval mode)

| Variant | Evidence hit | Page hit | Page recall | MRR | Kept? |
|---|---|---|---|---|---|
| Baseline: hash vectors, char-window chunker | 9/18 | 66.7% | 0.493 | 0.431 | — |
| E1: sentence chunker + soft-hyphen rejoin, vectors only | 9/18 | 66.7% | 0.479 | 0.363 | no, no gain alone |
| E2: E1 + hybrid BM25/vector RRF | **13/18** | 88.9% | 0.656 | 0.479 | chunker replaced (see E2b) |
| E3: E2 + demote TOC/index chunks | 13/18 | 88.9% | 0.656 | 0.479 | **reverted**, identical numbers |
| E2b: E2 with chunk-overlap bug fixed | 12/18 | 94.4% | 0.729 | 0.474 | no |
| Ablation: hybrid + original chunker | 12/18 | 94.4% | **0.740** | **0.546** | — |
| **Final:** hybrid + original chunker + soft-hyphen rejoin | 12/18 | 94.4% | 0.729 | 0.509 | **yes** |

Hybrid retrieval is the only change with a clear effect. The chunking variants sit within ±1
question of each other, so the existing chunker was kept rather than tuning to 18 questions.
The E2 sentence chunker carried almost no overlap (a bug), which likely inflated its single extra hit.

## Findings for the next iteration

1. **Remaining misses are vocabulary gaps** hash/lexical retrieval can't bridge ("define overfitting" →
   "tendency … to tailor models to the training data"). Real semantic embeddings are the next lever.
   The bundled `models/qualcomm/all-MiniLM-L6-v2/model.onnx` is **not** MiniLM: `scripts/setup_qualcomm_onnx_models.py`
   builds a single random-weight `Gather` node.
2. **Partial refusals:** `RetrievalService.chat` drops all sources when the answer contains
   "Insufficient evidence" anywhere. That hides legitimate cited partial answers (demo Q04), but it also
   hides answers with ungrounded content: in book B11, Qwen listed the CRISP-DM stages from training
   data, then refused. Decide a policy (e.g. keep sources and flag `partial`) before changing it.
3. **The score threshold is a poor abstention signal.** Unanswerable top-1 scores overlap answerable
   ones on the book, and it causes demo Q09's refusal. Qwen abstained correctly on 4/4 unanswerable
   questions, but that is too few to justify removing the gate. Add more unanswerable questions first.
4. **Math glyphs are lost at extraction.** pypdf emits only half of each surrogate pair for math italic
   symbols, so formulas become `p(� | �)`. Fixing that needs a different extractor.
5. The academic section-header regex mislabels book chunks (e.g. "Results" on p54).
