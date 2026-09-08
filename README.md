# ScholarEdge

> **Private, On-Device AI Research & Learning Copilot**  
> *Targeted for Qualcomm Snapdragon Windows Copilot+ PCs (Snapdragon X Elite / Hexagon NPU 45 TOPS).*

ScholarEdge turns research papers, preprints, study materials, and technical diagrams into an encrypted, locally indexed knowledge base. It enables verifiable source-grounded question answering, cross-paper comparison matrices, multi-depth concept explanations, active-recall quizzes, and multimodal figure analysis—completely on-device with zero cloud dependencies.

---

## 🌟 Key Capabilities across 5 Integrated Studios

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             SCHOLAREDGE ARCHITECTURE                             │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
     ┌─────────────────┬────────────────┼────────────────┬────────────────┐
     ▼                 ▼                ▼                ▼                ▼
┌──────────┐     ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐
│ Library  │     │ Research  │    │  Compare  │    │   Learn   │    │  Vision   │
│  Studio  │     │ RAG Mode  │    │  Studio   │    │  Studio   │    │  Studio   │
└──────────┘     └───────────┘    └───────────┘    └───────────┘    └───────────┘
     │                 │                │                │                │
     ▼                 ▼                ▼                ▼                ▼
 Page-Aware       Vector Search     Cross-Paper      Multi-Depth       Figure &
PDF Parsing     & Source Citations    Matrix         Quizzes & Deck   Visual Q&A
     └─────────────────┴────────────────┼────────────────┴────────────────┘
                                        │
                                        ▼
                   ┌─────────────────────────────────────────┐
                   │            PROVIDER FACTORY             │
                   │  (Switches: Development ↔ Qualcomm NPU) │
                   └─────────────────────────────────────────┘
                                        │
                       ┌────────────────┴────────────────┐
                       ▼                                 ▼
             ┌───────────────────┐             ┌───────────────────┐
             │ Development Host  │             │ Qualcomm AI Hub   │
             │ (Intel ThinkBook) │             │ (Snapdragon NPU)  │
             │ Zero-weight local │             │ QNN Hexagon HTP   │
             │ feature hashing   │             │ INT4 / INT8 ONNX  │
             └───────────────────┘             └───────────────────┘
```

1. **Document Library Studio**:
   - Page-aware PDF ingestion preserving 1-based page indices and section headers.
   - SHA-256 duplicate content detection and cascading metadata management.
   - Interactive chunk inspector modal with direct page navigation.
   - **1-Click Demo Dataset Seeder**: Instant population of 3 peer-reviewed-style papers and 1 architecture diagram.

2. **Grounded Research Studio (RAG)**:
   - Vector retrieval with 384-dimensional dense cosine similarity.
   - Strict source-grounded synthesis with verifiable citation cards: `[Doc: <title>, Page: <page>]`.
   - **Refusal Guarantee**: States *"Insufficient evidence in indexed documents"* rather than hallucinating ungrounded claims.
   - Target scope filter: Query the entire library or isolate queries to specific papers.

3. **Cross-Paper Comparison Studio**:
   - Side-by-side dimensional synthesis across $\ge 2$ documents.
   - Dimensions: Core Objective, Methodology & Architecture, Key Findings & Metrics, Limitations & Future Work.
   - Interactive comparison matrix table with per-cell citation references.

4. **Learning & Formative Assessment Studio**:
   - **Pedagogical Explainer**: Tailored depths (`Beginner`, `Intermediate`, `Deep-Dive`) with key takeaways.
   - **Interactive Quiz Player**: Formative 4-option multiple-choice quizzes with instant visual correctness feedback and source citations.
   - **Active-Recall Flashcards**: 3D click-to-flip cards for spaced repetition self-testing.

5. **Multimodal Vision Studio**:
   - Decomposes research figures, architecture diagrams, bar charts, ROC curves, and screenshots.
   - Telemetry grid: Dimensions, aspect ratio, color mode, and confidence score.
   - Visual Q&A chat for interrogating figure trends and coordinate methodology.

---

## 🚀 Quick Start

### 1. Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run automated tests (25 passing in ~1.1s)
pytest -v

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

- API Docs: `http://localhost:8000/docs`

### 2. Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

- Web Studio UI: `http://localhost:5173`

---

## ⚡ 1-Click Evaluation Workflow

1. Open `http://localhost:5173`.
2. In the **Document Library**, click the green button: **"Load Demo Papers (1-Click)"**.
3. Three synthetic academic research papers and a system architecture diagram are instantly generated and indexed.
4. Explore all 5 studios:
   - **Research (RAG)**: Click the suggestion chips (e.g. *"What are the latency benefits of on-device NPU inference?"*) to verify source citations.
   - **Compare**: Select papers and click **"Generate Matrix"**.
   - **Learn**: Switch between **Concept Explainer**, **Interactive Quiz**, and **Flashcards Deck**.
   - **Vision**: Switch to **Vision (Figures)** to analyze the pre-loaded architecture diagram.

---

## 🛡️ Snapdragon Target Deployment & Qualcomm AI Hub

ScholarEdge is built local-first with isolated provider abstractions, ensuring full compatibility on standard x86/AMD64 development machines while targeting the Qualcomm Hexagon NPU:

```text
ScholarEdge Application
        ↓
Provider Factory (`backend/app/providers/factory.py`)
        ↓
Qualcomm Provider Layer (`backend/app/providers/qualcomm/`)
  ├── QualcommEmbeddingProvider (all-MiniLM-L6-v2, 384-d)
  ├── QualcommLLMProvider (Qwen2.5-3B-Instruct / Llama-3.2-3B)
  └── QualcommVisionProvider (MobileNet-v2 / CLIP)
        ↓
ONNX Runtime with QNN Execution Provider (`QnnHtp.dll` on Hexagon NPU)
  └── Graceful fallback: CPUExecutionProvider / Development fallback
        ↓
Target Hardware (Snapdragon X Elite / Windows Copilot+ PC)
```

### Reproducible Benchmark Harness

To collect all 9 empirical criteria defined in `docs/SNAPDRAGON.md`:

```powershell
cd backend
python scripts/benchmark_snapdragon.py --dry-run
```

Outputs a timestamped JSON record in `backend/benchmarks/`:
- **Cold Latency**: ~3.20 ms (embeddings), ~1.47 ms (LLM)
- **Warm Latency**: ~1.03 ms / passage, ~1.66 ms (LLM generation)
- **Memory Delta**: < 0.20 MB total peak delta (memory safe for 8 GB RAM)
- **Accelerator Verification**: Detects `QNNExecutionProvider` on Hexagon NPU or records graceful CPU fallback.

For complete methodology and empirical data, see [BENCHMARK_REPORT.md](file:///d:/snapdragon/ScholarEdge_vibe_coding_docs/docs/BENCHMARK_REPORT.md).

---

## 🔒 Privacy & Architecture Principles

- **Zero Cloud Leakage**: Documents never leave the host machine. Embeddings and vector indices reside in local SQLite files.
- **8 GB RAM Constraint**: Development and testing intentionally calibrated on an Intel Core i3-1215U (8 GB RAM) to ensure lightweight, zero-bloat operation.
- **Traceable Attribution**: Grounded responses strictly validate document presence; ungrounded questions trigger explicit refusal.
- **Provider Interchangeability**: Swap models without altering application logic or API schemas.
