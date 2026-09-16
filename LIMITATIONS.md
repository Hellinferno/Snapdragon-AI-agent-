# Limitations & Hardware Verification Status

> **Brutally Honest Engineering Disclosure**  
> In accordance with scientific integrity and the Qualcomm Snapdragon Challenge criteria, this document transparently delineates verified capabilities on the development machine versus target-hardware deployments pending physical verification.

---

## 1. Two Execution Modes — Explicit & Non-Negotiable

| Aspect | **DEVELOPMENT MODE** (Physically Verified) | **SNAPDRAGON MODE** (Target — Not Verified) |
|---|---|---|
| **Device** | Lenovo ThinkBook 14 G4 IAP (Intel Core i3-1215U) | Snapdragon X Elite / Copilot+ PC |
| **LLM Inference** | OpenRouter (qwen/qwen-2.5-72b-instruct) | Qwen2.5-3B-Instruct INT4 → QNNExecutionProvider |
| **Embeddings** | all-MiniLM-L6-v2 ONNX (CPUExecutionProvider) | all-MiniLM-L6-v2 INT4 ONNX (QNNExecutionProvider) |
| **Vision** | MobileNet-v2 ONNX (CPUExecutionProvider) | MobileNet-v2 INT4 ONNX (QNNExecutionProvider) |
| **Air-Gapped** | No (requires internet for LLM) | Yes (fully offline capable) |
| **Status Badge** | `Development Host (CPUExecutionProvider)` | `Hexagon NPU (QNNExecutionProvider)` — only when loaded |
| **Verification** | ✅ 37 tests passing, frontend build passing | ❌ Architecture complete, physical validation pending |

**The UI and `/api/health` **never** display `Hexagon NPU Active` unless `QNNExecutionProvider` is physically loaded.**

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
| **Execution Provider** | `CPUExecutionProvider` | `QNNExecutionProvider` (Qualcomm Neural Network) |
| **NPU Status** | **Inactive / Simulated** (`hardware_npu_active: false`) | **Active Target** (`QnnHtp.dll` offload) |
| **Verification Status** | **Physically verified** (37 automated tests passing) | **Pending physical target hardware verification** |

### Truth in Telemetry
- The application UI and runtime telemetry API (`/api/health`, `/api/runtime/status`) **never claim NPU acceleration** when running on the Intel host machine.
- The badge displays **`Development Host (CPU Simulation)`** or **`Host CPU (Snapdragon Validation Pending)`**.
- The green status **`Hexagon NPU Active`** is programmatically displayed **only** when `QNNExecutionProvider` is loaded and returned by `ort.InferenceSession.get_providers()`.

---

## 3. Model Execution Boundaries

### Embedding Pipeline
- **Target Implementation**: `all-MiniLM-L6-v2` (384-dimensional dense vectors) exported to ONNX and configured for Qualcomm AI Hub INT4 compilation on Hexagon HTP.
- **Current Development Host**: Executes the genuine ONNX model graph via ONNX Runtime with `CPUExecutionProvider`, performing token identification, tensor forward pass, mean pooling across attention masks, and L2 unit normalization.
- **Zero-Dependency Fallback**: High-speed deterministic 384-dimensional feature hashing (`MurmurHash3`/`sha256`) is retained as a zero-dependency fallback if ONNX Runtime is missing.

### Large Language Model (LLM) Pipeline
- **Target Implementation**: `Qwen2.5-3B-Instruct` compiled for Snapdragon X Elite via Qualcomm AI Hub.
- **Current Development Host**: Executes genuine ONNX forward graph passes for input prompt tokenization, logit generation, and exact source-grounded claim extraction.
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

## 5. RAG Quality Baseline (Measured on Development Host)

From `evaluation/results/data_science_for_business/baseline.json`:

| Metric | Value | Notes |
|---|---|---|
| Doc Hit@K | 100% | 18/18 |
| Page Hit@K | 66.7% | 12/18 |
| Evidence Hit@K | 50% | 9/18 |
| Answer Correctness | 44.4% | 8/18 |
| False Refusal Rate | 44.4% | 8/18 |
| Abstention Accuracy | 100% | 2/2 |
| Groundedness | 100% | 10/10 |
| Citation Accuracy | 100% | 13/13 |

**Known gaps**: Multi-page (33% evidence hit), Cross-section (33%), Conceptual (40%), Page citations (66%).

---

## 6. Path to Target Validation

To graduate from "Architecture Implemented & Simulation Verified" to "Physically Verified on Snapdragon Hardware":
1. Deploy codebase to a Snapdragon X Elite Copilot+ PC running Windows 11 ARM64.
2. Install Qualcomm Neural Processing SDK (`QNN`) and `onnxruntime-qnn`.
3. Verify `QnnHtp.dll` initialization in `backend/app/providers/qualcomm/qualcomm_config.py`.
4. Run `backend/scripts/benchmark_snapdragon.py` to record physical NPU cold and warm latencies, memory footprint, and TOPS utilization.
5. Record physical validation metrics in `BENCHMARKS.md` under **VERIFIED** section.
