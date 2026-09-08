# Demonstrable Privacy Architecture & Data Governance

> **ScholarEdge: Verified 100% Local-First, Air-Gapped Operation**

---

## 1. Demonstrable Privacy Audit Checklist

ScholarEdge provides continuous verification of its local-first privacy boundary via both the web UI and the `/api/health` telemetry endpoint:

| Verification Check | Architectural Implementation | Audit Status |
|---|---|:---:|
| **1. Local Document Storage** | PDF files and extracted page representations reside exclusively in local SQLite database and `./backend/data/` filesystem directory. | **✓ VERIFIED LOCAL** |
| **2. Local Embedding Storage** | 384-dimensional dense vectors stored in local SQLite `chunks` table; no cloud vector databases (Pinecone, Weaviate, etc.) contacted. | **✓ VERIFIED LOCAL** |
| **3. Local Vector Search** | Cosine similarity scoring computed entirely on host CPU or Hexagon NPU using local memory; zero query text transmitted externally. | **✓ VERIFIED LOCAL** |
| **4. Local AI Inference** | Embedding generation, LLM synthesis, and figure classification executed via local ONNX Runtime / QNN without remote LLM endpoints. | **✓ VERIFIED LOCAL** |
| **5. No Document Upload** | Zero document, page, or excerpt payloads are dispatched to external endpoints; operates seamlessly in full airplane/air-gapped mode. | **✓ VERIFIED LOCAL** |
| **6. External Providers Disabled** | External cloud providers (e.g. Gemini, OpenAI) disabled by default (`AI_PROVIDER=development` or `AI_PROVIDER=qualcomm`). | **✓ VERIFIED LOCAL** |

---

## 2. Air-Gapped Offline Mode Test

ScholarEdge is engineered to maintain complete functionality when entirely disconnected from the internet:

```text
[INTERNET DISCONNECTED / AIRPLANE MODE]
  ├── Document Library PDF Upload: ACTIVE (PyMuPDF Local)
  ├── Page-Aware Chunker: ACTIVE (Regex & Layout Local)
  ├── Vector Indexing: ACTIVE (MiniLM ONNX / QNN Local)
  ├── Semantic Search & Q&A: ACTIVE (Cosine Similarity Local)
  ├── Cross-Paper Comparison: ACTIVE (Structured Synthesis Local)
  ├── Active-Recall Quiz & Flashcards: ACTIVE (Local Formative Engine)
  └── Multimodal Vision Studio: ACTIVE (MobileNet ONNX Local)
```

### Verification Procedure:
1. Turn off Wi-Fi or disconnect Ethernet on the host machine.
2. In the Document Library, upload a research PDF or click "Load Demo Papers (1-Click)".
3. Ask research queries, generate comparative synthesis matrices, play active-recall quizzes, and upload figures.
4. Open the **Hardware & Privacy Runtime Inspector** from the header badge or sidebar to verify that all 6 privacy checks remain green.

---

## 3. Clinical & Research Compliance

- **HIPAA (Health Insurance Portability and Accountability Act)**: Clinical research documents containing Protected Health Information (PHI) remain strictly on the clinician's or researcher's physical device.
- **GDPR (General Data Protection Regulation)**: Ensures compliance with data minimization, purpose limitation, and zero third-party cross-border transfers.
- **Proprietary IP Protection**: Academic papers under peer review and corporate patents are safeguarded from unauthorized ingestion into public model training corpuses.
