# ScholarEdge

> **Private, On-Device AI Research & Learning Copilot**
> *Designed for Qualcomm Snapdragon Copilot+ PCs (Snapdragon X Elite, Hexagon NPU). Currently verified on an Intel development host; Snapdragon execution is not yet physically validated.*

[![Automated Tests](https://img.shields.io/badge/pytest-125%20hermetic%20tests-10b981.svg)](DEVELOPMENT.md)
[![Frontend Build](https://img.shields.io/badge/vite-build%20passing-38bdf8.svg)](DEVELOPMENT.md)
[![Privacy](https://img.shields.io/badge/privacy-documents%20%26%20retrieval%20local%20%7C%20dev%20LLM%20cloud-f59e0b.svg)](PRIVACY.md)
[![Hardware Status](https://img.shields.io/badge/runtime-Intel%20i3%20Verified%20%7C%20Snapdragon%20NPU%20Pending-f59e0b.svg)](LIMITATIONS.md)

---

## 💡 Why Snapdragon for Research AI?

Research work — parsing dense PDFs, semantic search, cross-paper comparison, active-recall study,
and figure analysis — often involves unpublished manuscripts, trial data, or clinical material.

1. **Data confidentiality**: Sensitive research and clinical data may be subject to institutional,
   contractual, or legal restrictions. ScholarEdge's Snapdragon architecture is designed to reduce
   external data exposure by performing inference locally.
2. **Heterogeneous compute (target design)**:
   - **Hexagon NPU**: embedding generation (MiniLM via QNN) and LLM generation (Qwen3-4B via QAIRT / GenieX).
   - **Oryon CPU**: PDF parsing, chunking, and exact cosine-similarity retrieval over SQLite.
3. **Offline use**: once the LLM runs locally, the whole research loop is designed to work without a
   network connection (not yet tested on hardware — see [PRIVACY.md](PRIVACY.md)).

---

## 🏛️ System Architecture

### Development mode (Intel host — verified)

```text
PDF
 ↓
PyMuPDF (page-aware text extraction)
 ↓
all-MiniLM-L6-v2 embeddings (ONNX Runtime, CPUExecutionProvider)
 ↓
SQLite (chunks + vectors)
 ↓
Local cosine retrieval (host CPU)
 ↓
LLM generation via OpenRouter (development configuration; cloud)
```

### Snapdragon mode (target — not yet physically validated)

```text
PDF
 ↓
PyMuPDF
 ↓
all-MiniLM-L6-v2 ONNX
 ↓
QNN → Hexagon NPU            (embedding generation)
 ↓
SQLite
 ↓
Local retrieval              (cosine similarity on the host CPU, not the NPU)
 ↓
Qwen3-4B-Instruct-2507
 ↓
QAIRT / GenieX → Hexagon NPU (bundle detected, tokenizer loads; inference not yet implemented)
```

The two NPU paths are deliberately separate runtimes: MiniLM runs through **ONNX Runtime + QNN**,
while Qwen3 runs through **QAIRT / GenieX**. The Qwen3 bundle is not converted to ONNX.

**Figure analysis** runs on the CPU (in Snapdragon mode too, with `VISION_PROVIDER=development`): it measures pixel statistics (resolution,
colour, brightness, contrast, background, edge density) and derives a coarse figure category with
explicit rules. No trained figure classifier exists yet, so no model confidence is reported. See
[LIMITATIONS.md](LIMITATIONS.md#3-model-execution-boundaries).

---

## 🔍 Verified vs Target vs Not Yet Verified

### ✅ Verified (Lenovo ThinkBook 14 G4 IAP)

```text
Intel Core i3-1215U · 8 GB RAM · Windows 11 · AMD64
ONNX Runtime CPUExecutionProvider (MiniLM embeddings)
125 hermetic tests (0 API keys, 0 network required)
RAG evaluation (committed result files, see BENCHMARKS.md)
Frontend build
Complete application workflow (Library → Research → Compare → Learn → Vision → Runtime Inspector)
```

### 🎯 Target architecture

```text
Snapdragon X Elite → Hexagon NPU → QNN          → MiniLM (embeddings)
Qwen3-4B-Instruct-2507 → QAIRT / GenieX → Hexagon NPU
```

### ❌ Not yet verified

```text
Physical Snapdragon execution
Qwen3 QAIRT generation
NPU latency, tokens/sec, power consumption
Air-gapped physical test
A trained figure classifier (MobileNet-v2 path is scaffolding only)
```

**Truthful telemetry**: the header badge and the Runtime Inspector read `/api/health`, which reports the
providers that were actually resolved. On the Intel host they show `Dev Host (CPU)` and, while
OpenRouter is configured, `Cloud LLM in use`. `Hexagon NPU Active` appears only when a component reports
physical NPU execution.

*Full disclosure: [LIMITATIONS.md](LIMITATIONS.md).*

---

## 🌟 The 5 Studios

```text
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Library    │ → │   Research   │ → │   Compare    │ → │    Learn     │ → │    Vision    │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
  Page-aware         Grounded RAG       Evidence-based      Explainer, quiz,   Figure analysis +
  ingestion &        with page          comparison with     retry loop,        paper-grounded
  chunk inspector    citations          cited quotes        flashcards         cited context
```

### 1. Library
- Page-aware PDF ingestion that preserves 1-based page numbers and section headings.
- SHA-256 duplicate detection; retry for failed parses.
- Document inspector with **Extracted Chunks** and **Raw Pages** views.
- **Load Demo Papers (1-Click)** seeds three synthetic clinical-AI papers and an architecture diagram.

### 2. Research (grounded RAG)
- 384-dimensional MiniLM retrieval with exact cosine similarity.
- Citations carry paper, page, section, chunk ID and relevance score.
- **View Source Excerpt** opens the document inspector, scrolls to the cited chunk and highlights it.
- **Grounded refusal**: questions the indexed documents cannot answer return
  *"Insufficient evidence in the indexed documents to answer this question."* When a question asks for
  several things and only some are reported, the answer says which ones are missing.

### 3. Compare (evidence-based comparison)
- Dimensions: **Research objective, Methodology, Dataset, Model / architecture, Metrics, Results,
  Limitations, Trade-offs**.
- Every cell quotes one sentence from the paper with a page citation that opens the exact chunk.
  Nothing in the comparison is generated.
- **Evidence gaps**: a dimension a paper does not address is shown as a gap instead of being filled.
- **Which paper better matches this criterion?** For each criterion you enter, the evidence from every
  paper is shown with its similarity score; a paper is named only when it is clearly ahead. This
  measures how directly a paper addresses the criterion, not which paper is better.

### 4. Learn
- **Concept explainer** at Beginner, Intermediate and Deep-Dive levels.
- **4-tier quizzes** (Easy, Medium, Hard, Research-Level) with an answer key, explanation, source
  page and a **Retry Question** loop.
- **Flashcards** for active recall.
- A generated explanation, question or card is kept only if it cites a retrieved passage — and, for
  quizzes and cards, only if that passage actually states the answer. Otherwise the studio falls back
  to quoting the passage and says so.

### 5. Vision (multimodal figure analysis)
- On-device figure analysis from measured pixel statistics: resolution, aspect ratio, colour mode,
  brightness, contrast, dominant background, edge density, and a rule-based figure category.
- **Paper-grounded Q&A**: link a paper and each answer adds cited passages retrieved from it; every
  citation opens the exact chunk.
- It does not read the figure's text, axes, values or trends, and it says so rather than guessing.
  This is on-device figure classification plus paper-grounded analysis, not a vision-language model.

---

## 🛡️ Privacy Modes

### Development mode (current, verified)

```text
Documents / embeddings / vector store / retrieval:  local
Comparison and figure analysis:                      local (no LLM)
LLM generation:                                      OpenRouter (question + retrieved excerpts are sent)
Air-gapped:                                          No
Verified on:                                         Lenovo ThinkBook 14 G4 IAP (Intel i3-1215U, 8 GB, Windows 11)
```

### Snapdragon mode (target — not yet physically validated)

```text
Embeddings:        all-MiniLM-L6-v2 ONNX → QNN → Hexagon NPU
Vector store:      SQLite (local)
Retrieval:         cosine similarity on the host CPU
LLM:               Qwen3-4B-Instruct-2507 → QAIRT / GenieX → Hexagon NPU (inference not yet implemented)
Air-gapped:        designed for it; not yet tested on hardware
```

Details, including exactly what leaves the machine in development mode: [PRIVACY.md](PRIVACY.md).

---

## 📊 Measured RAG Quality (development host)

Full mode (retrieval + generation), MiniLM embeddings, vector-only retrieval, top-k = 5. The numbers,
their configuration and the per-question detail live in the committed result files; see
[BENCHMARKS.md](BENCHMARKS.md#rag-quality-development-host).

| Metric              |    409-page book |   Demo papers |
| ------------------- | ---------------: | ------------: |
| Evidence Hit@5      |    17/18 (94.4%) |  13/13 (100%) |
| Page Hit@5          |     18/18 (100%) |  13/13 (100%) |
| Answer correctness  |    17/18 (94.4%) | 12/13 (92.3%) |
| False refusals      | 1/18 (5.6%, B14) |          0/13 |
| Abstention accuracy |       2/2 (100%) |    2/2 (100%) |
| Groundedness        |    16/17 (94.1%) |  13/13 (100%) |

> Evaluation performed on the development laptop with the same settings as the frozen baseline.
> Qualcomm NPU execution was not available on this machine.

Result files: `backend/evaluation/results/data_science_for_business/final_full_k5.json` and
`backend/evaluation/results/demo_papers/final_full_k5.json`. The generator is the OpenRouter development model, so these measure the
RAG pipeline on the development host, not Snapdragon performance.

---

## ⚡ Quick Start

### 1. Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 125 hermetic tests: 0 API keys, 0 network required
pytest -v

# Start the API
uvicorn app.main:app --reload --port 8000
```
- API docs: `http://localhost:8000/docs`
- Health & runtime telemetry: `http://localhost:8000/api/health`

On a host without the Qualcomm ONNX/QAIRT artifacts (such as the Intel development laptop), 7 of the
hermetic tests skip because the artifact they exercise is absent; none fail.

**Optional live integration tests** (separate from the hermetic suite; require an OpenRouter API key
and internet):
```powershell
$env:RUN_LIVE_TESTS = "1"; $env:OPENROUTER_API_KEY = "sk-..."
pytest -m integration
```

### 2. Frontend
```powershell
cd frontend
npm install
npm run build
npm run dev
```
- Studio interface: `http://localhost:5173`

---

## 📚 Documentation

| Document | Purpose |
|---|---|
| [README.md](README.md) | Overview, architecture, verified vs target status, studio guide. |
| [LIMITATIONS.md](LIMITATIONS.md) | What is verified on the development host and what is pending on Snapdragon. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Pipelines, data flow, provider factory, telemetry contract. |
| [SNAPDRAGON.md](SNAPDRAGON.md) | Snapdragon deployment and the physical validation checklist. |
| [MODEL_CATALOG.md](MODEL_CATALOG.md) | MiniLM-L6-v2, Qwen3-4B-Instruct-2507, and the figure-analysis path. |
| [BENCHMARKS.md](BENCHMARKS.md) | Measured RAG quality and the Snapdragon benchmark protocol. |
| [PRIVACY.md](PRIVACY.md) | What stays local in each mode, the privacy checklist, and the air-gapped test. |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Developer setup and test execution. |
| [DEMO.md](DEMO.md) | Step-by-step demo script for reviewers. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution standards. |
