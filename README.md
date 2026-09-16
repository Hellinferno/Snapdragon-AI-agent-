# ScholarEdge

> **Private, On-Device AI Research & Learning Copilot**  
> *Engineered for Qualcomm Snapdragon Copilot+ PCs (Snapdragon X Elite / Hexagon NPU 45 TOPS).*

[![Automated Tests](https://img.shields.io/badge/pytest-37%20passed-10b981.svg)](DEVELOPMENT.md)
[![Frontend Build](https://img.shields.io/badge/vite-build%20passing-38bdf8.svg)](DEVELOPMENT.md)
[![Privacy Mode](https://img.shields.io/badge/privacy-100%25%20local--first-emerald.svg)](PRIVACY.md)
[![Hardware Status](https://img.shields.io/badge/runtime-Intel%20i3%20Verified%20%7C%20Snapdragon%20NPU%20Pending-f59e0b.svg)](LIMITATIONS.md)

---

## 💡 Why Snapdragon for Research AI?

Research AI workloads—dense PDF parsing, vector embedding generation, multi-paper comparative synthesis, active-recall formative assessments, and multimodal figure analysis—represent the **ideal archetype for private on-device edge computing**:

```text
Research PDF ──► Semantic RAG ──► MiniLM Embedding ──► Qwen LLM ──► MobileNet Vision ──► Hexagon NPU
 (Confidential)    (Local-First)      (384-dim INT4)      (INT4 QNN)      (INT4 QNN)       (45 TOPS)
```

1. **Uncompromised Data Confidentiality**: Medical trials, unpublished research papers, patent applications, and clinical health data (PHI) cannot legally or ethically be transmitted to third-party cloud APIs under HIPAA and GDPR. Snapdragon Copilot+ PCs execute all embeddings, vector ranking, and language models 100% on-device.
2. **Heterogeneous Compute Architecture**: Modern research analysis demands diverse computing resources:
   - **Qualcomm Hexagon NPU (45 TOPS)**: High-throughput, ultra-efficient INT4/INT8 tensor acceleration for continuous vector indexing and prompt processing under a 4.5W power envelope.
   - **Qualcomm Oryon CPU**: 12 high-performance cores for multi-threaded PDF layout decomposition, vector graphics parsing, and OCR.
   - **Qualcomm Adreno GPU**: Fluid hardware-accelerated rendering of the 5-Studio interface, interactive comparison matrices, and 3D flashcards.
3. **All-Day Battery Life**: Researchers, clinicians, and students require sustained AI intelligence in clinical rounds, libraries, and fieldwork without cloud tethering or thermal throttling.

---

## 🏛️ System Execution Architecture

ScholarEdge implements genuine ONNX Runtime execution with explicit execution provider separation for **two modes**:

### Development Mode (Intel Host — Verified)

```text
                            ScholarEdge Application
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           ↓                           ↓                           ↓
  Embedding Engine                LLM Engine                Vision Engine
 (all-MiniLM-L6-v2 ONNX)      (OpenRouter: Qwen 2.5 72B)   (MobileNet-v2 ONNX)
           │                           │                           │
           └───────────────────────────┼───────────────────────────┘
                                       ↓
                                 ONNX Runtime
                         (ort.InferenceSession v1.20+)
                                       │
                           ┌───────────┴───────────┐
                           ▼                       ▼
                  CPUExecutionProvider        CPUExecutionProvider
                           │                       │
                           ▼                       ▼
                     Intel Core i3              Intel Core i3
                    (Development Host)        (Development Host)
```

### Snapdragon Mode (Target — Not Yet Physically Validated)

```text
                            ScholarEdge Application
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           ↓                           ↓                           ↓
  Embedding Engine                LLM Engine                Vision Engine
 (all-MiniLM-L6-v2 INT4 ONNX)  (Qwen2.5-3B-Instruct INT4)  (MobileNet-v2 INT4 ONNX)
           │                           │                           │
           └───────────────────────────┼───────────────────────────┘
                                       ↓
                                 ONNX Runtime
                         (ort.InferenceSession v1.20+)
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
           QNNExecutionProvider                   QNNExecutionProvider
                      │                                 │
                      ▼                                 ▼
           Snapdragon Hexagon NPU                Snapdragon Hexagon NPU
               (45 TOPS INT4)                       (45 TOPS INT4)
         [Target Hardware Execution]           [Target Hardware Execution]
```

---

## 🔍 Hardware Verification & Truth in Telemetry

In accordance with strict scientific honesty:

| Aspect | Development Host (Verified) | Snapdragon Target (Pending) |
|--------|----------------------------|----------------------------|
| **Hardware** | Lenovo ThinkBook 14 G4 IAP (Intel Core i3-1215U, 8 GB RAM, Windows 11 AMD64) | Snapdragon X Elite / Hexagon NPU 45 TOPS |
| **Tests** | 37 backend tests passing, frontend build passing | Architecture implemented, ONNX graphs exported, provider isolation complete |
| **LLM Inference** | OpenRouter (qwen/qwen-2.5-72b-instruct) | Qwen2.5-3B-Instruct INT4 → QNNExecutionProvider |
| **Embeddings** | all-MiniLM-L6-v2 ONNX (CPUExecutionProvider) | all-MiniLM-L6-v2 INT4 ONNX (QNNExecutionProvider) |
| **Vision** | MobileNet-v2 ONNX (CPUExecutionProvider) | MobileNet-v2 INT4 ONNX (QNNExecutionProvider) |
| **Air-Gapped** | No (requires internet for LLM) | Yes (fully offline capable) |
| **Status Badge** | ✅ Physically Verified | ❌ Not Physically Verified |

**Truthful Status Display**:
- Development Host UI shows: `Development Host (CPUExecutionProvider)`
- Snapdragon PC UI shows: `Hexagon NPU (QNNExecutionProvider)` **only** when `QNNExecutionProvider` is physically loaded and executing

*Read our detailed disclosure in [LIMITATIONS.md](LIMITATIONS.md).*

---

## 🌟 The 5 Integrated Studios

```text
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Library    │   │   Research   │   │   Compare    │   │    Learn     │   │    Vision    │
│    Studio    │   │   RAG Mode   │   │    Studio    │   │    Studio    │   │    Studio    │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │                  │                  │
  Page-Aware         Semantic RAG       Structured          4-Tier Quiz        Researcher
 PDF Ingestion       & View Source      Synthesis &         & Mistake          Prompts &
 & 1-Click Demo      Citation Jump      Recommendations     Retry Loop         MobileNet
```

### 1. Document Library Studio
- Page-aware PDF ingestion preserving 1-based page indices and section headers.
- SHA-256 duplicate detection and retryable parsing for interrupted uploads.
- Interactive chunk inspector modal with direct page navigation.
- **1-Click Demo Dataset Seeder**: Instantly seeds 3 peer-reviewed-style Medical-AI research papers and an architecture diagram.

### 2. Grounded Research Studio (RAG)
- Dense 384-dimensional vector retrieval with cosine similarity ranking.
- **Claim-Level Citations**: Excerpts tagged with `Paper`, `Page`, `Section`, `Chunk ID`, and `Relevance Score`.
- **"View Source Excerpt" Click-Through**: Clicking a citation opens the Document Inspector, navigates to the exact chunk, and highlights it in glowing emerald.
- **Grounded Refusal Guarantee**: Strictly outputs *"Insufficient evidence in indexed documents"* on unsupported queries rather than hallucinating.

### 3. Cross-Paper Comparison Studio
- Structured dimensional comparison across $\ge 2$ documents (Objectives, Methodology, Metrics, Limitations).
- **LLM Synthesis**: Automatically identifies commonalities, methodological differences, performance differences, dataset differences, limitations, and contradictory findings.
- **Decision Recommendations ("Which Paper is Stronger for X?")**: Provides evidence-backed guidance for specific research and clinical scenarios.
- Side-by-side comparison matrix with per-cell citation references.

### 4. Learning & Formative Assessment Studio
- **Pedagogical Explainer**: Three conceptual depths (`Beginner`, `Intermediate`, `Deep-Dive`).
- **4-Tier Formative Quizzes**: Generates multiple-choice assessments across `Easy`, `Medium`, `Hard`, and `Research-Level` difficulties.
- **Formative Learning Loop**: Each question displays verified findings, pedagogical explanation, source paper, and a **"Retry Question (Analyze Mistake)"** loop.
- **Active-Recall Flashcards**: 3D interactive flip cards for spaced repetition.

### 5. Multimodal Vision Studio (Figure Analysis)
- MobileNet-v2 ONNX figure classification: `architecture_diagram`, `bar_chart`, `data_table`, `medical_radiograph`.
- Telemetry decomposition: Resolution, aspect ratio, color mode, and confidence score.
- **Researcher Quick Prompts**:
  - `📊 What does this graph show?` (Trend and distribution analysis)
  - `🔄 Explain the pipeline` (Architectural pipeline and flow)
  - `🔢 Extract the important numbers` (Tabular and comparative metrics)
  - `🔬 Describe observable structures` (Visual observations; zero unsupported clinical diagnoses)

---

## 🛡️ Privacy Modes: Development vs. Snapdragon

ScholarEdge operates in **two distinct modes**. The distinction is explicit and non-negotiable.

### DEVELOPMENT MODE (Current Verified State)

```text
Inference:        OpenRouter (qwen/qwen-2.5-72b-instruct)
Document retrieval: Local (SQLite + all-MiniLM-L6-v2 ONNX)
Documents uploaded to cloud: No
Embeddings uploaded to cloud: No
Vector search:    Local (zero network egress)
Air-gapped:       No (requires internet for LLM)
Verified on:      Lenovo ThinkBook 14 G4 IAP (Intel i3-1215U, 8 GB RAM, Windows 11)
Tests:            37 backend tests passing | Frontend build passing
```

### SNAPDRAGON MODE (Target — Not Yet Physically Validated)

```text
Inference:        Qwen2.5-3B-Instruct INT4 ONNX → QNNExecutionProvider → Hexagon NPU
Document retrieval: Local (SQLite + all-MiniLM-L6-v2 INT4 ONNX → QNNExecutionProvider → Hexagon NPU)
Documents uploaded to cloud: No
Embeddings uploaded to cloud: No
Vector search:    Local (zero network egress)
Air-gapped:       Yes (fully offline capable)
Target hardware:  Snapdragon X Elite / Hexagon NPU (45 TOPS)
Status:           Architecture implemented, ONNX graphs exported, provider isolation complete
                  PHYSICAL VALIDATION PENDING
```

**The UI Hardware Inspector displays `Host CPU (Development)` or `Hexagon NPU (Verified)` — never assumes Snapdragon execution without `QNNExecutionProvider` physically loaded.**

**Air-Gapped Offline Guarantee (Snapdragon Mode only)**: Disconnect the internet or switch to airplane mode—ScholarEdge continues complete operation with zero interruption.

---

## ⚡ Quick Start

### 1. Backend Setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run automated tests (37 passing in ~4.9s)
pytest -v

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Health & Runtime Telemetry: `http://localhost:8000/api/health`

### 2. Frontend Setup
```powershell
cd frontend
npm install
npm run build
npm run dev
```
- Studio Interface: `http://localhost:5173`

---

## 📚 Complete Repository Documentation

| Document | Purpose |
|---|---|
| [README.md](README.md) | Project overview, "Why Snapdragon?", architecture, and studio guide. |
| [LIMITATIONS.md](LIMITATIONS.md) | **Brutally honest** disclosure of development host vs Snapdragon target status. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System pipeline diagrams, data flow, and provider factory abstractions. |
| [SNAPDRAGON.md](SNAPDRAGON.md) | Snapdragon Copilot+ PC deployment, QNN SDK, and HTP offload guide. |
| [MODEL_CATALOG.md](MODEL_CATALOG.md) | Specifications for MiniLM-L6-v2, Qwen2.5-3B, and MobileNet-v2. |
| [BENCHMARKS.md](BENCHMARKS.md) | Benchmark methodology, measured host latencies, and Snapdragon target profiles. |
| [PRIVACY.md](PRIVACY.md) | Demonstrable local-first checklist, air-gapped test, and HIPAA/GDPR compliance. |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Developer onboarding, environment setup, and test execution. |
| [DEMO.md](DEMO.md) | Step-by-step evaluation script for challenge reviewers. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution standards, code style, and PR requirements. |
