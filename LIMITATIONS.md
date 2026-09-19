# Limitations & Hardware Verification Status

> **Brutally Honest Engineering Disclosure**  
> In accordance with scientific integrity and the Qualcomm Snapdragon Challenge criteria, this document transparently delineates verified capabilities on the development machine versus target-hardware deployments pending physical verification.

---

## 1. Two Execution Modes — Explicit & Non-Negotiable

| Aspect | **DEVELOPMENT MODE** (Physically Verified) | **SNAPDRAGON MODE** (Target — Not Verified) |
|---|---|---|
| **Device** | Lenovo ThinkBook 14 G4 IAP (Intel Core i3-1215U) | Snapdragon X Elite / Copilot+ PC |
| **LLM Inference** | OpenRouter (configured development model) | Qwen3-4B-Instruct-2507 INT4 → GenieX/QAIRT → Hexagon NPU (inference pending) |
| **Embeddings** | all-MiniLM-L6-v2 ONNX (CPUExecutionProvider) — auto-selected when the model is present, otherwise the feature-hash fallback (reported as `embedding_degraded` by `/api/health`) | all-MiniLM-L6-v2 INT4 ONNX (QNNExecutionProvider) |
| **Vision** | MobileNet-v2 ONNX (CPUExecutionProvider) | MobileNet-v2 INT4 ONNX (QNNExecutionProvider) |
| **Air-Gapped** | No (requires internet for LLM) | Yes (fully offline capable) |
| **Status Badge** | `Development Host (CPUExecutionProvider)` | `Hexagon NPU (GenieX/QAIRT)` — only when loaded |
| **Verification** | ✅ 119 hermetic tests, frontend build passing | ❌ Architecture complete, physical validation pending |

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
| **Verification Status** | **Physically verified** (119 automated tests) | **Pending physical target hardware verification** |

### Truth in Telemetry
- The application UI and runtime telemetry API (`/api/health`, `/api/runtime/status`) **never claim NPU acceleration** when running on the Intel host machine.
- The badge displays **`Development Host (CPU Simulation)`** or **`Host CPU (Snapdragon Validation Pending)`**.
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
- **Grounding Guarantee**: When evidence is missing or below relevance threshold, the system strictly outputs:  
  `"Insufficient evidence in indexed documents to answer this question grounded in peer-reviewed sources."`  
  It will never hallucinate fabricated findings.

### Multimodal Vision Pipeline
- **Target Implementation**: `MobileNet-v2` / `MobileNet-v4` figure classifier and structural feature extractor compiled via Qualcomm AI Hub for Hexagon NPU.
- **Current Development Host**: Genuine image preprocessing (224×224 RGB resize, ImageNet channel mean subtraction, standard deviation normalization into `[1, 3, 224, 224]` float32 tensors) followed by ONNX model forward pass for figure classification (`architecture_diagram`, `bar_chart`, `data_table`, `medical_radiograph`).
- **Limitation**: The vision pipeline currently performs **figure decomposition, visual feature extraction, and structural classification**. It does **not** yet run an end-to-end 7B Multimodal VQA model on the 8 GB development machine to prevent out-of-memory crashes.

---

## 4. Dataset & Document Support
- **Supported Formats**: Text-rich PDF documents (peer-reviewed papers, clinical reports, conference proceedings).
- **OCR Capability**: PDF page parsing with fallback OCR triggers. Non-PDF files (e.g. raw `.docx`, `.pptx`) must be converted to PDF prior to ingestion.
- **Storage Scope**: SQLite database and filesystem storage reside strictly on the local machine (`backend/data/`). Zero external network egress occurs during indexing, vector search, or synthesis.

---

## 5. RAG Quality (Measured on Development Host)

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

The demo corpus is committed, so those rows reproduce with no arguments beyond `--dataset demo_papers`.
Ranking on it is frozen by `backend/tests/test_retrieval_regression.py`.

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
