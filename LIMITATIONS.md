# Limitations & Hardware Verification Status

> **Brutally Honest Engineering Disclosure**  
> In accordance with scientific integrity and the Qualcomm Snapdragon Challenge criteria, this document transparently delineates verified capabilities on the development machine versus target-hardware deployments pending physical verification.

---

## 0. Known Limitations (summary)

**Development uses the OpenRouter cloud API. Fully local/offline Snapdragon inference remains pending hardware and QAIRT/GenieX validation.**

- **Snapdragon hardware validation is pending**: nothing has run on a physical Snapdragon device.
- **Qwen3 QAIRT generation is not implemented or validated**: the bundle is detected and its
  tokenizer loads; no token has been generated on the NPU.
- **No NPU latency, tokens/sec or power numbers exist**: none are measured, so none are published.
- **Air-gapped operation is not physically validated**: development mode needs the network for
  generation, and the Snapdragon offline test (PRIVACY.md §5) has not been run.
- **Figure semantic classification is not implemented**: vision measures pixel statistics and applies
  rules; it does not read text, values or trends, and no figure classifier has been trained.
- **OpenRouter is an external dependency in development**: generation needs the network and an API
  key, answers vary run to run, and upstream rate limits can fail a request (one full evaluation run
  crashed this way; see BENCHMARKS.md).
- **One book question still fails**: B14 (multi-hop, Chapter 3 vs Chapter 11) is refused because its
  Chapter 11 evidence is never retrieved; B06 is answered correctly but its evidence sentence misses
  the top 5.

---

## 1. Two Execution Modes — Explicit & Non-Negotiable

| Aspect | **DEVELOPMENT MODE** (Physically Verified) | **SNAPDRAGON MODE** (Target — Not Verified) |
|---|---|---|
| **Device** | Lenovo ThinkBook 14 G4 IAP (Intel Core i3-1215U) | Snapdragon X Elite / Copilot+ PC |
| **LLM Inference** | OpenRouter (configured development model) | Qwen3-4B-Instruct-2507 INT4 → GenieX/QAIRT → Hexagon NPU (inference pending) |
| **Embeddings** | all-MiniLM-L6-v2 ONNX (CPUExecutionProvider) — auto-selected when the model is present, otherwise the feature-hash fallback (reported as `embedding_degraded` by `/api/health`) | all-MiniLM-L6-v2 INT4 ONNX (QNNExecutionProvider) |
| **Vision** | Pixel-statistics figure analysis on the CPU (no neural model) | MobileNet-v2 ONNX (QNNExecutionProvider) — scaffolding only; no trained figure classifier yet |
| **Air-Gapped** | No (requires internet for LLM) | Designed for it; not yet tested on hardware |
| **Status Badge** | `Dev Host (CPU)` · `Cloud LLM in use` | `Hexagon NPU Active` — only when a component reports physical NPU execution |
| **Verification** | ✅ 125 hermetic tests, frontend build, full browser walkthrough of all five studios | ❌ Architecture complete, physical validation pending |

**The UI and `/api/health` never display LLM NPU execution without a validated QAIRT session. `QNNExecutionProvider` telemetry applies only to the ONNX embedding and vision paths.**

---

## 2. Hardware Execution & Host Environment

| Component | Development Machine (Verified) | Snapdragon PC (Target Architecture) |
|---|---|---|
| **Device Model** | Lenovo ThinkBook 14 G4 IAP | Qualcomm Snapdragon X Elite Reference / Copilot+ PC |
| **Processor** | 12th Gen Intel Core i3-1215U (6 cores / 8 threads) | Snapdragon X Elite (12 Oryon cores up to 3.8 GHz) |
| **System Architecture** | AMD64 / x86_64 | ARM64 / AArch64 |
| **Memory** | 8.00 GB DDR4 RAM | 16 GB - 32 GB LPDDR5x |
| **Operating System** | Windows 11 Pro 64-bit | Windows 11 on ARM (Build 26100+) |
| **AI Accelerator** | None (Host CPU only) | Qualcomm Hexagon NPU (45 TOPS) |
| **Execution Provider** | `CPUExecutionProvider` | `QNNExecutionProvider` (embeddings/vision); QAIRT / GenieX (LLM) |
| **NPU Status** | **Inactive / Simulated** (`hardware_npu_active: false`) | **Active Target** (`QnnHtp.dll` offload) |
| **Verification Status** | **Physically verified** (125 hermetic tests; 7 skip here because the Qualcomm artifacts are absent) | **Pending physical target hardware verification** |

### Truth in Telemetry
- The application UI and runtime telemetry API (`/api/health`, `/api/runtime/status`) **never claim NPU acceleration** when running on the Intel host machine.
- The header badge displays **`Dev Host (CPU)`**, plus **`Cloud LLM in use`** whenever generation is served by a cloud provider; the Runtime Inspector shows `NPU Status: Validation Pending (Host CPU)`.
- The green status **`Hexagon NPU Active`** is displayed only when the relevant component reports physical execution: `QNNExecutionProvider` for ONNX embedding/vision, or a validated QAIRT session for the LLM.

---

## 3. Model Execution Boundaries

### Embedding Pipeline
- **Target Implementation**: `all-MiniLM-L6-v2` (384-dimensional dense vectors) exported to ONNX and configured for Qualcomm AI Hub INT4 compilation on Hexagon HTP.
- **Current Development Host**: Executes the genuine ONNX model graph via ONNX Runtime with `CPUExecutionProvider`, performing token identification, tensor forward pass, mean pooling across attention masks, and L2 unit normalization.
- **Zero-Dependency Fallback**: High-speed deterministic 384-dimensional feature hashing (`sha256`) is retained as a zero-dependency fallback when the ONNX model or runtime is missing. It is selected automatically in that case and flagged as `embedding_degraded` in `/api/health` and in evaluation result files, with the measured cost named (44.4% vs 94.4% answer correctness on the book corpus, §5) — so a machine without the model cannot silently look like it is running semantic retrieval.

### Large Language Model (LLM) Pipeline
- **Target Implementation**: `Qwen3-4B-Instruct-2507` compiled for Snapdragon X Elite via Qualcomm AI Hub (QAIRT/GenieX format).
- **Current Development Host**: Detects the QAIRT bundle and loads its tokenizer, but cannot execute QAIRT inference on the Intel host.
- **Runtime**: GenAI Inference Extensions (GenieX/QAIRT) on Hexagon NPU (Snapdragon Mode) / Development fallback (Development Mode).
- **Grounded refusal**: when the retrieved evidence does not support an answer, the system prompt
  requires the exact reply `"Insufficient evidence in the indexed documents to answer this question."`
  This is enforced by the prompt and measured (abstention accuracy in §5), not guaranteed: the
  development LLM is a cloud model whose behaviour can drift.
- **Learning Studio checks**: a generated explanation, quiz question or flashcard is kept only if it
  cites a retrieved passage; quiz answers and flashcard backs must also be stated by that passage
  (numbers verbatim, at least half of the content words). Otherwise the studio falls back to quoting
  the passage and labels the result as extractive.
- **Comparison is extractive**: the Compare studio quotes one cited sentence per paper and dimension
  and reports evidence gaps; it makes no LLM call and does not rank papers as stronger or weaker.

### Figure Analysis (Vision) Pipeline
- **What runs today (development host)**: `DevelopmentVisionProvider` measures the image on the CPU —
  resolution, aspect ratio, colour mode, mean brightness, contrast (luminance standard deviation),
  dominant background colour and its share, number of colours in use, and edge density — and derives a
  coarse category (line-art figure; greyscale continuous-tone image; colour photograph) from explicit
  rules on those measurements. The category does not depend on the file name.
- **What it does not do**: it does not read text, axis labels, values or trends, and it reports no
  confidence score because nothing in it is probabilistic. Q&A answers what was measured, states what
  it cannot see, and — when a paper is linked — adds cited passages retrieved from that paper.
- **Snapdragon target**: `QualcommVisionProvider` is scaffolding for a MobileNet-v2 ONNX classifier via
  QNN. No trained figure classifier exists: the public MobileNet-v2 is an ImageNet classifier, and the
  provider's four figure classes (`architecture_diagram`, `bar_chart`, `data_table`,
  `medical_radiograph`) have no trained weights behind them. This path is not validated and makes no
  classification claim.
- **Not a vision-language model**: there is no end-to-end multimodal VQA model; an 8 GB development
  machine cannot host one alongside the rest of the stack.

---

## 4. Dataset & Document Support
- **Supported Formats**: Text-rich PDF documents (peer-reviewed papers, clinical reports, conference proceedings).
- **No OCR**: text comes from the PDF text layer via PyMuPDF. Scanned PDFs without a text layer produce empty pages (`ocr_used` is always `false`). Non-PDF files (e.g. `.docx`, `.pptx`) must be converted to PDF first.
- **Storage Scope**: SQLite database and filesystem storage reside strictly on the local machine (`backend/data/`). No network egress occurs during indexing or vector search; in development mode the LLM call is the only outbound traffic (see PRIVACY.md).

---

## 5. RAG Quality (Measured on Development Host)

**Final run after the last code changes** (`final_full_k5.json` for both datasets, MiniLM vector-only,
top-k = 5): book 17/18 answer correctness, 17/18 evidence hit, 1/18 false refusals (B14), 2/2
abstention, 16/17 groundedness (B12 answered without a citation in that run; it cited correctly in
3 of 3 isolated re-runs); demo papers 12/13 correct, 0/13 false refusals, 2/2 abstention, 13/13
grounded. Retrieval metrics are identical to the frozen configuration below. Full table:
[BENCHMARKS.md](BENCHMARKS.md#rag-quality-development-host).

Every number below comes from a committed result file named in the column header. Metric
definitions, per-question detail and the experiment log live in `backend/evaluation/README.md`,
which is the canonical source — this table is a summary of it, not a second copy.

**A single number is meaningless without its configuration.** The same dataset spans 44.4% to
94.4% answer correctness depending only on which embedding provider and retrieval mode are
selected, so configuration is a column, not a footnote.

### `data_science_for_business` (409-page book, 18 answerable + 2 unanswerable questions)

Full mode (retrieval + generation via OpenRouter qwen-2.5-72b-instruct), top-k = 5:

| Metric | `baseline.json` (hash, vector-only) | `p1_hybrid.json` (hash + BM25) | `head_full_k5.json` (MiniLM, vector-only) | `p1b_minilm_hybrid.json` (MiniLM + BM25) |
|---|---|---|---|---|
| Evidence Hit@5 | 9/18 (50.0%) | 12/18 (66.7%) | **17/18 (94.4%)** | 16/18 (88.9%) |
| Page Hit@5 | 12/18 (66.7%) | 17/18 (94.4%) | **18/18 (100%)** | 18/18 (100%) |
| Page recall@5 | 0.493 | 0.729 | **0.812** | 0.784 |
| MRR | 0.431 | 0.509 | **0.681** | 0.630 |
| Answer Correctness | 8/18 (44.4%) | 13/18 (72.2%) | **17/18 (94.4%)** | 15/18 (83.3%) |
| False Refusal Rate | 8/18 (44.4%) | 1/18 (5.6%) | **1/18 (5.6%)** | 1/18 (5.6%) |
| Abstention Accuracy | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) |

What this says, and what it does not:

- **Real semantic embeddings are the whole story** (44.4% → 94.4%). The largest single lever is not
  reranking, thresholds, or chunking — it is not using sha256 feature hashes for semantic search.
- **With MiniLM, BM25 fusion costs one retrieval hit and two correct answers** (94.4% → 83.3%), which
  is why the retrieval default follows the embedding provider: fusion is only the right default when
  the vectors are the weak signal (44.4% → 72.2% with hashing).
- **Hit@k saturates at this corpus size and cannot rank configurations.** Doc hit is 100% even with
  feature hashing. MRR and page recall@k are the discriminating metrics.
- **Abstention, groundedness and citation accuracy are 100% in every configuration**, so they are not
  evidence of retrieval quality; they are evidence that the refusal and citation plumbing works.

Retrieval-mode top-k sweep (MiniLM, vector-only, from `head_retrieval_k{3,5,8,10}.json`):

| k | Evidence Hit | Page Hit | Page recall | MRR |
|---|---|---|---|---|
| 3 | 88.9% | 94.4% | 0.773 | 0.667 |
| 5 | 94.4% | 100% | 0.812 | 0.681 |
| 8 | 94.4% | 100% | 0.840 | 0.681 |
| 10 | 94.4% | 100% | 0.868 | 0.681 |

(BM25 at k = 10, `head_retrieval_k10_hybrid.json`, reaches 100% evidence hit but a *lower* MRR of
0.649, i.e. it buys recall by pushing relevant chunks down — the precision-for-recall trade that
`precision_at_k`, added to the harness with this change, now reports.)

### `demo_papers` (3 synthetic clinical papers, 13 answerable + 2 unanswerable questions)

Retrieval metrics; full-mode correctness for the recommended configuration is 12/13 (92.3%),
false refusals 0/13, in `p1b_minilm.json` (committed alongside `baseline.json`, `p1_hybrid.json`
and `p1b_minilm_hybrid.json`).

| Metric | `baseline.json` (hash, vector-only) | `p1_hybrid.json` (hash + BM25) | `p1b_minilm.json` (MiniLM, vector-only) | `p1b_minilm_hybrid.json` (MiniLM + BM25) |
|---|---|---|---|---|
| Doc Hit@5 | 100% | 100% | 100% | 100% |
| Page Hit@5 | 92.3% | 100% | 100% | 100% |
| Evidence Hit@5 | 92.3% | 100% | 100% | 100% |
| Page recall@5 | 0.692 | 0.750 | **0.923** | 0.923 |
| MRR | 0.718 | 0.872 | 0.821 | **0.910** |

On this corpus BM25 fusion *helps* MRR even with semantic embeddings — the opposite of the book
corpus — because 15 chunks total leave little for a generic-keyword promotion to displace. Full-mode
correctness is 12/13 either way, so the disagreement is confined to ranking, and the book corpus
(1,900 chunks, realistic scale) is the one the default follows.

### Reproducing these numbers

The book's PDF is not redistributed (copyright), so its rows need the corpus locally:

```bash
cd backend
# recommended configuration (this is also the automatic default)
python -m evaluation.run_eval --dataset data_science_for_business --corpus-dir .. --mode retrieval
# the four configurations above
python -m evaluation.run_eval --dataset data_science_for_business --corpus-dir .. \
        --embedding-provider development --no-hybrid   # 44.4%-class
python -m evaluation.run_eval --dataset data_science_for_business --corpus-dir .. \
        --embedding-provider development --hybrid      # 72.2%-class
python -m evaluation.run_eval --dataset data_science_for_business --corpus-dir .. \
        --embedding-provider onnx_minilm --hybrid      # 83.3%-class
```

PDFs are kept out of git, so the demo rows reproduce only where the pinned demo PDFs exist in
`backend/evaluation/corpus/demo_papers`; elsewhere, regenerate them with `scripts/generate_demo_papers.py`
and re-pin the hashes (reportlab embeds a timestamp, so regenerated bytes differ). Ranking on it is
frozen by `backend/tests/test_retrieval_regression.py`, which skips where the pinned PDFs are absent.

`precision_at_k` was added to the harness with this change, so the pre-existing result files above do
not contain it; the values recorded in this document are the ones they do contain.

**Known gaps**: the single cross-document synthesis miss on the demo corpus (50% on one category);
page recall@k 0.812 on the book, where multi-page evidence spans are capped by retrieving the
neighbouring page before the exact one. Neither is a reranking problem — with MiniLM the first
relevant chunk is already at rank ≤ 3 for 17/18 book questions.

---

## 6. Path to Target Validation

To graduate from "Architecture Implemented & Simulation Verified" to "Physically Verified on Snapdragon Hardware":
1. Deploy codebase to a Snapdragon X Elite Copilot+ PC running Windows 11 ARM64.
2. Install Qualcomm Neural Processing SDK (`QNN`), `onnxruntime-qnn` for embeddings/vision, and GenAI Inference Extensions for the LLM.
3. Verify `QnnHtp.dll` initialization in `backend/app/providers/qualcomm/qualcomm_config.py`.
4. Implement and validate the QAIRT generation session on the target device before running LLM benchmarks.
5. Run `backend/scripts/benchmark_snapdragon.py` and record only reproducible physical measurements in `BENCHMARKS.md`.
