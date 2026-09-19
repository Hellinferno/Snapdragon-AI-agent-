# Privacy Architecture & Data Handling

> **The architecture is designed for local/on-device inference. The current development configuration uses OpenRouter for LLM generation; fully local Snapdragon operation remains pending hardware validation.**

Sensitive research and clinical data may be subject to institutional, contractual, or legal
restrictions. ScholarEdge's Snapdragon architecture is designed to reduce external data exposure
by performing inference locally. This document describes what stays on the device in each mode
and how to check it; it is not a compliance certification.

---

## 1. Privacy Modes at a Glance

This distinction must stay identical across README.md, DEMO.md, and this document.

### Development Mode (current, verified on the Intel host)

```text
Documents          → LOCAL (SQLite + filesystem)
Embeddings         → LOCAL (all-MiniLM-L6-v2, ONNX Runtime, CPU)
Vector store       → LOCAL (SQLite)
Retrieval          → LOCAL (exact cosine similarity, host CPU)
Comparison         → LOCAL (extractive, no LLM)
Figure analysis    → LOCAL (pixel statistics, no LLM)
LLM generation     → OpenRouter (cloud) — receives the question + retrieved excerpts
Internet required  → YES (for generation only)
```

### Snapdragon Mode (target, pending physical validation)

```text
Documents          → LOCAL (SQLite + filesystem)
Embeddings         → all-MiniLM-L6-v2 ONNX → QNN → Hexagon NPU
Vector store       → LOCAL (SQLite)
Retrieval          → LOCAL (exact cosine similarity, host CPU — not the NPU)
LLM generation     → Qwen3-4B-Instruct-2507 → QAIRT / GenieX → Hexagon NPU (inference not yet implemented)
Internet required  → NO (by design; the air-gapped test has not been run on hardware)
```

| Check | **DEVELOPMENT MODE** (current) | **SNAPDRAGON MODE** (target) |
|---|---|---|
| **Local document storage** | ✅ Verified (SQLite + filesystem) | 🎯 Target |
| **Local embedding storage** | ✅ Verified (SQLite vectors) | 🎯 Target |
| **Local vector search** | ✅ Verified (cosine similarity on the host CPU) | 🎯 Target (cosine similarity on the host CPU) |
| **AI inference** | ⚠️ OpenRouter (cloud LLM) | 🎯 Local (QAIRT / GenieX on the NPU) |
| **No excerpt leaves the device** | ❌ Retrieved excerpts are sent to OpenRouter | 🎯 Target |
| **External providers** | ⚠️ OpenRouter enabled | 🎯 Disabled by default |
| **Air-gapped operation** | ❌ No (generation needs internet) | 🎯 Designed for it; not yet tested on hardware |

---

## 2. What Leaves the Machine in Development Mode

The only outbound traffic is the LLM call. It is made by these features, and only these:

| Feature | Sent to OpenRouter | Stays on the device |
|---|---|---|
| Research chat | the question + the top-k retrieved excerpts | the PDF, other pages, embeddings |
| Learn: explainer, quiz, flashcards | the concept/task + retrieved excerpts | the PDF, other pages, embeddings |
| Compare | nothing (extractive) | everything |
| Vision / figure analysis | nothing (pixel statistics + local retrieval) | the image and everything else |
| Library, search, document inspector | nothing | everything |

---

## 3. Privacy Checklist — Development Mode (Verified)

The web UI (header badge and the **Hardware & Privacy Runtime Inspector**) and `/api/health` report
this checklist from the provider that was actually resolved, not from configuration:

| Verification check | Implementation | Status |
|---|---|:---:|
| **1. Local document storage** | PDF files and extracted pages live in the local SQLite database and `./backend/data/`. | **✅ LOCAL** |
| **2. Local embedding storage** | 384-dimensional vectors are stored in the local SQLite database; no cloud vector database is contacted. | **✅ LOCAL** |
| **3. Local vector search** | Exact cosine similarity computed on the host CPU; query text is not sent anywhere for retrieval. | **✅ LOCAL** |
| **4. AI inference** | Generation via OpenRouter (internet required). Embeddings, retrieval, comparison and figure analysis are local. | **⚠️ CLOUD LLM** |
| **5. No document upload** | Whole documents are never uploaded, but retrieved excerpts are sent to OpenRouter for generation. | **⚠️ EXCERPTS SENT** |
| **6. External providers** | OpenRouter enabled via `ALLOW_EXTERNAL_PROVIDERS=true`. | **⚠️ ENABLED** |

---

## 4. Privacy Checklist — Snapdragon Mode (Target)

| Verification check | Implementation | Status |
|---|---|:---:|
| **1. Local document storage** | Same as development mode. | **🎯 TARGET** |
| **2. Local embedding storage** | Same as development mode; embeddings are computed by MiniLM ONNX via QNN on the Hexagon NPU. | **🎯 TARGET** |
| **3. Local vector search** | Exact cosine similarity on the host CPU. The vector search itself is not an NPU workload in this design. | **🎯 TARGET** |
| **4. AI inference** | LLM → Qwen3-4B-Instruct-2507 via QAIRT / GenieX on the Hexagon NPU; embeddings → MiniLM ONNX via QNN. | **🎯 TARGET** |
| **5. No document upload** | Designed so that no document, page, or excerpt needs to leave the device. | **🎯 TARGET** |
| **6. External providers** | Disabled (`ALLOW_EXTERNAL_PROVIDERS=false`, the default); `OPENROUTER_API_KEY` is ignored. | **🎯 TARGET** |

---

## 5. Air-Gapped Test — Snapdragon Mode Only (Not Yet Performed)

**Development mode cannot run air-gapped**, because generation uses OpenRouter.

Snapdragon mode is designed to run with the network disconnected. This procedure has **not yet been
executed on physical Snapdragon hardware**; it is the test to run once QAIRT generation works:

```text
[INTERNET DISCONNECTED — SNAPDRAGON MODE — EXPECTED BEHAVIOUR]
  ├── Document upload & parsing: PyMuPDF (local)
  ├── Page-aware chunking: local
  ├── Embedding generation: MiniLM ONNX via QNN (Hexagon NPU)
  ├── Retrieval: cosine similarity (host CPU)
  ├── Grounded chat, explainer, quiz, flashcards: Qwen3-4B via QAIRT / GenieX (Hexagon NPU)
  ├── Comparison: extractive (local, no LLM)
  └── Figure analysis: pixel statistics + local retrieval
```

### Procedure (Snapdragon mode)
1. Turn off Wi-Fi and disconnect Ethernet on the Snapdragon Copilot+ PC.
2. In the Library, upload a PDF or click **Load Demo Papers (1-Click)**.
3. Ask research questions, run a comparison, generate a quiz, and analyse a figure.
4. Open the **Hardware & Privacy Runtime Inspector** and confirm that all six checks are green and that
   the NPU status reports physical execution.

---

## 6. Technical Privacy Properties (Snapdragon Mode Target)

These are properties of the design. They become verified claims only after the air-gapped test
above passes on physical hardware.

- **Local inference**: embedding generation and LLM generation run on the device, so no query text,
  retrieved excerpt, or document content needs to leave it.
- **No outbound traffic by default**: external providers are disabled unless explicitly enabled, and
  no telemetry is sent to model providers.
- **Data minimisation**: only the question and the retrieved excerpts are placed in the LLM prompt;
  whole documents never enter the context window.
- **Local retrieval**: vectors are stored in SQLite and compared on the host CPU.
- **Inspectable**: `/api/health` and the Runtime Inspector report what is actually executing, so a
  fallback to a cloud provider is visible rather than silent.

---

## 7. Development Workflow Note

During development, generation uses **OpenRouter (`qwen/qwen-2.5-72b-instruct`)**. That means:

- the **question and the retrieved excerpts** are sent to OpenRouter's API;
- **documents, embeddings, and vector search** remain local;
- the demo corpus is synthetic, so no real patient or proprietary data is involved in the demo.

Do not load confidential documents in development mode. Fully local operation is the Snapdragon-mode
target described above.
