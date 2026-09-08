# ScholarEdge

> **Private, On-Device AI Research & Learning Copilot**  
> *Targeted for Qualcomm Snapdragon Windows Copilot+ PCs (Snapdragon X Elite / Hexagon NPU 45 TOPS).*

> [!NOTE]
> **Hardware Verification Status**:
> - **Verified Development Workflow**: Lenovo ThinkBook 14 G4 IAP (Intel Core i3-1215U, 8 GB RAM, Windows 11 Pro AMD64). All 5 studios, vector indexing, citation tracking, and 31 automated tests verified passing.
> - **Snapdragon Deployment**: Architecture, provider isolation, and candidate model abstractions implemented. On-device Qualcomm Hexagon NPU execution is **PENDING TARGET-DEVICE VALIDATION** per the checklist below.

ScholarEdge turns research papers, clinical trial reports, study materials, and technical diagrams into a source-grounded, private knowledge base. It enables verifiable source-grounded question answering, cross-paper comparison matrices, multi-depth concept explanations, active-recall quizzes, and multimodal figure analysis—operating local-first with zero external cloud transmission by default.

---

## 🌟 5 Integrated Studios

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
             │ Zero-weight local │             │ Candidate Models: │
             │ feature hashing   │             │ INT4 / INT8 ONNX  │
             └───────────────────┘             └───────────────────┘
```

1. **Document Library Studio**:
   - Page-aware PDF ingestion preserving 1-based page indices and section headers.
   - SHA-256 duplicate content detection and retryable ingestion for failed documents.
   - Interactive chunk inspector modal with direct page navigation.
   - **1-Click Demo Dataset Seeder**: Instantly seeds 3 peer-reviewed-style Medical-AI research papers and 1 architecture diagram.

2. **Grounded Research Studio (RAG)**:
   - Dense vector retrieval with 384-dimensional cosine similarity.
   - Strict source-grounded synthesis with verifiable citation cards: `[Doc: <title>, Page: <page>]`.
   - **Grounded Refusal Guarantee**: Refuses ungrounded queries with *"Insufficient evidence in indexed documents"* rather than hallucinating.
   - Target scope filter: Query the entire library or isolate queries to specific papers.

3. **Cross-Paper Comparison Studio**:
   - Side-by-side dimensional synthesis across $\ge 2$ documents.
   - Dimensions: Core Objective, Methodology & Architecture, Key Findings & Metrics, Limitations & Future Work.
   - Interactive comparison matrix table with per-cell citation references.

4. **Learning & Formative Assessment Studio**:
   - **Pedagogical Explainer**: Tailored depths (`Beginner`, `Intermediate`, `Deep-Dive`) with evidence-grounded takeaways.
   - **Interactive Quiz Player**: Formative 4-option multiple-choice quizzes with instant visual correctness feedback and source citations.
   - **Active-Recall Flashcards**: 3D click-to-flip cards for spaced repetition self-testing.

5. **Multimodal Vision Studio (Figure Analysis)**:
   - Decomposes research figures, architecture diagrams, charts, and clinical scans into structural observations, metrics, and type classification.
   - Telemetry grid: Dimensions, aspect ratio, color mode, and confidence score.
   - Visual Q&A chat for interrogating figure trends and coordinate methodology.
   - *Honest Capability Boundary*: Currently operates via development heuristic decomposition; full Qualcomm Hexagon NPU vision acceleration requires physical target ONNX Runtime QNN integration with Qualcomm AI Hub vision models (e.g. MobileNet-v4 / ResNet-50).

---

## 📋 Target-Device Validation Checklist

Physical validation on a Snapdragon Windows Copilot+ PC requires recording the following evidence:

| Check | Item | Target Requirement | Status |
|:---:|---|---|:---:|
| 1 | **Architecture** | ARM64 Windows 11 (`platform.machine() == 'ARM64'`) | ⏳ Pending Physical Target |
| 2 | **Model Artifacts** | Qualcomm AI Hub models downloaded with SHA-256 hash log | ⏳ Pending Physical Target |
| 3 | **Runtime Engine** | `onnxruntime-qnn` installed (`QNNExecutionProvider` detected) | ⏳ Pending Physical Target |
| 4 | **QNN Backend** | Qualcomm Hexagon HTP backend (`QnnHtp.dll`) session initialized | ⏳ Pending Physical Target |
| 5 | **NPU Latency** | Cold and warm latency measured via `scripts/benchmark_snapdragon.py` | ⏳ Pending Physical Target |
| 6 | **Memory Footprint** | Peak RAM delta and NPU allocation verified under 8 GB ceiling | ⏳ Pending Physical Target |
| 7 | **Profiling Output** | QNN operator offload report confirming Hexagon NPU execution | ⏳ Pending Physical Target |

---

## 🚀 Quick Start

### 1. Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run automated tests (31 passing in ~1.3s)
pytest -v

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

- API Docs: `http://localhost:8000/docs`
- Health Telemetry: `http://localhost:8000/api/health`

### 2. Frontend Setup

```powershell
cd frontend
npm install
node --test src/api.test.js
npm run dev
```

- Web Studio UI: `http://localhost:5173`

---

## ⚡ 1-Click Evaluation Workflow

1. Open `http://localhost:5173`.
2. In the **Document Library**, click the green button: **"Load Demo Papers (1-Click)"**.
3. Three synthetic **Medical-AI research papers** and an architecture diagram are indexed:
   - *Clinical Multimodal Transformers for Diagnostic Radiology*
   - *Privacy-Preserving On-Device Clinical Language Models*
   - *Formative Assessment and Active Recall in Medical Education*
4. Explore all 5 studios:
   - **Research (RAG)**: Click the suggestion chips:
     - *"Pneumonia AUC? (Direct)"* → Verifies 91.4% AUC and page 4 citation.
     - *"Clinical Privacy? (Direct)"* → Verifies on-device PHI HIPAA justification.
     - *"Pediatric dosage? (Refusal Test)"* → Confirms refusal without hallucination.
   - **Compare**: Select papers and click **"Generate Matrix"**.
   - **Learn**: Switch between **Concept Explainer**, **Interactive Quiz**, and **Flashcards Deck**.
   - **Vision**: Switch to **Vision (Figures)** to analyze the pre-loaded architecture diagram.

---

## 🛡️ Snapdragon Architecture & Benchmark Harness

ScholarEdge cleanly isolates AI execution via provider abstractions:

```powershell
cd backend
python scripts/benchmark_snapdragon.py --dry-run
```

**Development Host Baseline Measurements (Intel Core i3-1215U, 8 GB RAM):**
- **Benchmark Mode**: `DEVELOPMENT_HOST_SIMULATION` (clearly labeled baseline)
- **Target Checklist**: `PENDING TARGET-DEVICE VALIDATION`
- **Embedding Latency**: Cold: ~2.46 ms | Warm (10-chunk batch): ~10.15 ms
- **LLM Latency**: Cold: ~1.66 ms | Warm: ~4.39 ms (Python host simulation)
- **Memory Footprint**: Peak RAM Delta < 0.20 MB (memory-safe for 8 GB RAM)

*Note: All latency figures above represent host simulation baseline. Hardware NPU acceleration is marked pending target-device validation.*

---

## 🔒 Privacy & Grounding Guarantees

- **Local-First by Default**: Raw documents, embeddings, and vector indices reside in local SQLite storage.
- **Opt-in External Providers**: External cloud providers (e.g. Gemini) are disabled by default (`ALLOW_EXTERNAL_PROVIDERS=false`) and require explicit opt-in.
- **Strict Grounding**: Every answer, comparison cell, quiz explanation, and flashcard retains a source citation or returns an explicit insufficient-evidence state.
- **8 GB RAM Safe**: Architecture designed to operate within 8 GB RAM constraints without memory pressure.
