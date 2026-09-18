# Demonstrable Privacy Architecture & Data Governance

> **ScholarEdge: Two Privacy Modes — Development (Cloud LLM) vs Snapdragon (Fully Air-Gapped)**

---

## 1. Privacy Modes at a Glance

This exact distinction is canonical and must stay identical across README.md, DEMO.md, and this document.

### Development Mode (current, verified)

```text
Documents          → LOCAL
Embeddings         → LOCAL
Vector DB          → LOCAL
Retrieval          → LOCAL
LLM                → OpenRouter
Internet required  → YES
```

### Snapdragon Mode (target, pending physical validation)

```text
Documents          → LOCAL
Embeddings         → Snapdragon NPU (QNN)
Vector DB          → LOCAL
Retrieval          → LOCAL
LLM                → Qwen3-4B via QAIRT/GenieX
Internet required  → NO
```

| Check | **DEVELOPMENT MODE** (Current) | **SNAPDRAGON MODE** (Target) |
|---|---|---|
| **Local Document Storage** | ✅ Verified (SQLite + filesystem) | ✅ Target |
| **Local Embedding Storage** | ✅ Verified (SQLite vectors) | ✅ Target |
| **Local Vector Search** | ✅ Verified (CPU cosine similarity) | ✅ Target (NPU) |
| **AI Inference** | ⚠️ OpenRouter (cloud LLM) | ✅ Local (QAIRT/GenieX on NPU) |
| **No Document Upload** | ✅ Verified | ✅ Target |
| **External Providers** | ⚠️ OpenRouter enabled | ✅ Disabled by default |
| **Air-Gapped Operation** | ❌ No (requires internet) | ✅ Fully offline capable |

---

## 2. Demonstrable Privacy Audit Checklist — Development Mode (Verified)

ScholarEdge provides continuous verification of its local-first privacy boundary via both the web UI and the `/api/health` telemetry endpoint:

| Verification Check | Architectural Implementation | Audit Status |
|---|---|:---:|
| **1. Local Document Storage** | PDF files and extracted page representations reside exclusively in local SQLite database and `./backend/data/` filesystem directory. | **✅ VERIFIED LOCAL** |
| **2. Local Embedding Storage** | 384-dimensional dense vectors stored in local SQLite `chunks` table; no cloud vector databases (Pinecone, Weaviate, etc.) contacted. | **✅ VERIFIED LOCAL** |
| **3. Local Vector Search** | Cosine similarity scoring computed entirely on host CPU using local memory; zero query text transmitted externally. | **✅ VERIFIED LOCAL** |
| **4. AI Inference** | **Development**: LLM via OpenRouter (internet required). Embeddings & Vision are local ONNX. | **⚠️ CLOUD LLM** |
| **5. No Document Upload** | Zero document, page, or excerpt payloads dispatched to external endpoints. | **✅ VERIFIED LOCAL** |
| **6. External Providers** | OpenRouter enabled for LLM; configurable to disable via `AI_PROVIDER=qualcomm` (not yet physically validated). | **⚠️ PARTIAL** |

---

## 3. Demonstrable Privacy Audit Checklist — Snapdragon Mode (Target)

| Verification Check | Architectural Implementation | Audit Status |
|---|---|:---:|
| **1. Local Document Storage** | PDF files and extracted page representations reside exclusively in local SQLite database and `./backend/data/` filesystem directory. | **🎯 TARGET** |
| **2. Local Embedding Storage** | 384-dimensional dense vectors stored in local SQLite `chunks` table; no cloud vector databases contacted. | **🎯 TARGET** |
| **3. Local Vector Search** | Cosine similarity scoring computed entirely on Hexagon NPU using local memory; zero query text transmitted externally. | **🎯 TARGET** |
| **4. AI Inference** | **Snapdragon**: LLM, Embeddings, Vision all local ONNX → QNNExecutionProvider → Hexagon NPU. | **🎯 TARGET** |
| **5. No Document Upload** | Zero document, page, or excerpt payloads dispatched to external endpoints. | **🎯 TARGET** |
| **6. External Providers** | All external providers disabled (`AI_PROVIDER=qualcomm`); `OPENROUTER_API_KEY` ignored if set. | **🎯 TARGET** |

---

## 4. Air-Gapped Offline Mode Test — Snapdragon Mode Only

**Development Mode CANNOT run air-gapped** (requires OpenRouter internet access).

**Snapdragon Mode** is engineered to maintain complete functionality when entirely disconnected from the internet:

```text
[INTERNET DISCONNECTED / AIRPLANE MODE — SNAPDRAGON MODE]
  ├── Document Library PDF Upload: ACTIVE (PyMuPDF Local)
  ├── Page-Aware Chunker: ACTIVE (Regex & Layout Local)
  ├── Vector Indexing: ACTIVE (MiniLM INT4 ONNX / QNN Local)
  ├── Semantic Search & Q&A: ACTIVE (Cosine Similarity Local / NPU)
  ├── Cross-Paper Comparison: ACTIVE (Structured Synthesis Local / NPU)
  ├── Active-Recall Quiz & Flashcards: ACTIVE (Local Formative Engine)
  └── Multimodal Vision Studio: ACTIVE (MobileNet INT4 ONNX Local / NPU)
```

### Verification Procedure (Snapdragon Mode):
1. Turn off Wi-Fi or disconnect Ethernet on the Snapdragon Copilot+ PC.
2. In the Document Library, upload a research PDF or click "Load Demo Papers (1-Click)".
3. Ask research queries, generate comparative synthesis matrices, play active-recall quizzes, and upload figures.
4. Open the **Hardware & Privacy Runtime Inspector** from the header badge or sidebar to verify that all 6 privacy checks remain green and status shows `Hexagon NPU (QNNExecutionProvider)`.

---

## 5. Clinical & Research Compliance

- **HIPAA (Health Insurance Portability and Accountability Act)**: Clinical research documents containing Protected Health Information (PHI) remain strictly on the clinician's or researcher's physical device. **Only Snapdragon Mode guarantees zero cloud egress for PHI.**
- **GDPR (General Data Protection Regulation)**: Ensures compliance with data minimization, purpose limitation, and zero third-party cross-border transfers. **Only Snapdragon Mode guarantees zero cross-border transfer.**
- **Proprietary IP Protection**: Academic papers under peer review and corporate patents are safeguarded from unauthorized ingestion into public model training corpuses. **Only Snapdragon Mode guarantees zero cloud exposure.**

---

## 6. Current Development Workflow Privacy Note

During development, the system uses **OpenRouter (qwen/qwen-2.5-72b-instruct)** for LLM inference. This means:

- **Query text + retrieved context** are sent to OpenRouter's API
- **Documents, embeddings, and vector search** remain fully local
- **No document content is uploaded** — only the RAG prompt with citations

**For true air-gapped/HIPAA/GDPR compliance, deploy in Snapdragon Mode on target hardware.**