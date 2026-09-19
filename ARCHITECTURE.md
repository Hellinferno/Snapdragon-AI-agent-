# ScholarEdge System Architecture

> **Private, On-Device AI Research & Learning Architecture**  
> Designed for heterogeneous execution on Qualcomm Snapdragon Copilot+ PCs with seamless host CPU development support.

---

## 1. High-Level System Architecture

```text
                                   ScholarEdge Application Layer
                                                │
                ┌───────────────────────────────┼───────────────────────────────┐
                ▼                               ▼                               ▼
       Document Library &              Vector Search &                 Multimodal Vision
        Page Chunker                     Compare Matrix                    Decomposition
                │                               │                               │
                └───────────────────────────────┼───────────────────────────────┘
                                                ▼
                                    Provider Factory Abstraction
                                                │
                ┌───────────────────────────────┼───────────────────────────────┐
                ▼                               ▼                               ▼
        Embedding Pipeline                 LLM Pipeline                  Vision Pipeline
       (all-MiniLM-L6-v2)              (Qwen3-4B-Instruct-2507)              (MobileNet-v2)
                │                               │                               │
                └───────────────────────────────┼───────────────────────────────┘
                                                ▼
                        ┌───────────────────────┴───────────────────────┐
                        ▼                                               ▼
               Embedding/Vision                          LLM
               ONNX Runtime                              GenieX/QAIRT
               (ort.InferenceSession)                    (GenieX Runtime)
                        │                                               │
           ┌────────────┴────────────┐                   ┌─────────────┴─────────────┐
           ▼                         ▼                   ▼                           ▼
    QNNExecutionProvider      QNNExecutionProvider   GenAI Inference           QAIRT Runtime
    (Embedding/Vision)          (Embedding/Vision)    Extensions (GenieX)       (QAIRT)
         │                           │                       │                         │
         ▼                           ▼                       ▼                         ▼
Qualcomm Hexagon HTP NPU      Qualcomm Hexagon HTP    Snapdragon X Elite        Snapdragon X Elite
(45 TOPS INT4 Embedding)      (45 TOPS INT4 Vision)   Hexagon NPU (45 TOPS)   Hexagon NPU (45 TOPS)
[Snapdragon Mode]             [Snapdragon Mode]       [Snapdragon Mode]       [Snapdragon Mode]
         │                           │                       │                         │
         └───────────────────────────┼───────────────────────┘                         │
                                      ▼                                                 ▼
                              [DEVELOPMENT HOST]                              [SNAPDRAGON HARDWARE]
                         CPUExecutionProvider (FP32)                   QAIRT/QNN on NPU
                         (FP32 Simulation)                            (INT4 on NPU)
```

---

## 2. Why Snapdragon for Research AI?

Research AI workloads (PDF document parsing, dense semantic embeddings, multi-paper comparative synthesis, active recall formative generation, and research figure analysis) are the **archetypal workload for private on-device edge computing**:

1. **Uncompromised Data Confidentiality**: Medical trials, unpublished manuscripts, institutional research, and patient health data (PHI) cannot legally or ethically be transmitted to external cloud APIs under HIPAA and GDPR. Snapdragon enables 100% on-device processing.
2. **Heterogeneous Compute Architecture**: Modern research analysis combines varied computational profiles:
   - **Hexagon NPU**: Dedicated matrix multiplication engine delivering **45 TOPS** at ultra-low power (4.5W sustained). Ideal for continuous background vector embedding and LLM prompt processing.
   - **Qualcomm Oryon CPU**: High-performance multi-threaded parsing of dense PDF layouts, font streams, and vector graphics.
   - **Adreno GPU**: Fluid hardware-accelerated rendering of the 5 Studio interface, 3D flashcards, and high-resolution figure previews.
3. **All-Day Battery Life & Portability**: Researchers and clinicians need continuous intelligence without tethering to cloud servers or high-wattage desktop GPUs. Snapdragon Copilot+ PCs deliver sustained inference under 5W NPU power envelopes.

---

## 3. End-to-End Processing Pipelines

### Pipeline A: PDF Ingestion & Semantic Indexing
```text
PDF Document ──► PyMuPDF Layout Parser ──► Page-Aware Chunker ──► MiniLM-L6-v2 ONNX ──► SQLite Vector Store
                  (Extract text, OCR,      (Preserve 1-based     (384-dim normalized     (Cosine similarity
                   section headers)         pages & sections)     tensors via QNN/NPU)    indexing)
```

### Pipeline B: Source-Grounded RAG Retrieval & Verification
```text
User Question ──► Vector Query Embedding ──► Top-K Cosine Retrieval ──► Reranking & Relevance Filter
                                                                                   │
                                                 ┌─────────────────────────────────┘
                                                 ▼
                                     Score >= Threshold?
                                     ├── No  ──► Explicit Refusal ("Insufficient evidence in indexed documents")
                                     └── Yes ──► Qwen3-4B-Instruct-2507 (GenieX/QAIRT)
                                                       │
                                                       ▼
                                                 Claim-Level Verification
                                                       │
                                                       ▼
                                                 Answer with Verifiable Citations
                                                 [Paper: X, Page: Y, Section: Z, Chunk: N]
                                                 └── "View Source Excerpt" modal jump
```

> **Note:** The LLM targets **GenAI Inference Extensions (GenieX/QAIRT)**, not ONNX Runtime. QAIRT bundle detection and tokenizer loading are implemented, but inference and physical NPU validation are pending. The embedding and vision pipelines continue to target ONNX Runtime with QNNExecutionProvider.
```

### Pipeline C: Multimodal Vision Analysis
```text
Research Figure ──► Image Preprocessing ──► MobileNet-v2 ONNX ──► Hexagon NPU / CPU ──► Structural Classification
                     (224x224 RGB, ImageNet    (QNN/CPU Session)                           (Architecture, Plot,
                      channel norm tensor)                                                 Table, Radiograph)
                                                                                                  │
                                                                                                  ▼
                                                                                      Targeted Visual Features &
                                                                                      Observation Decomposition
```

---

## 4. Hardware Telemetry & Runtime Inspection Contract

ScholarEdge maintains continuous hardware telemetry via `/api/health` and `/api/runtime/status`. Every
field below is derived from the provider that was **actually resolved**, not from the configured
string, so a machine that silently fell back cannot report the good configuration
(`embedding_degraded` exists for exactly that reason). This is the real development-host payload with
OpenRouter as the generation provider — note that three checklist rows are *not* green, because the
LLM leg does leave the device:

```json
{
  "status": "healthy",
  "device_name": "Windows AMD64 (Development Host / Non-Snapdragon)",
  "architecture": "AMD64",
  "runtime_engine": "ONNX Runtime (embeddings/vision); QAIRT pending (LLM)",
  "active_provider": "CPUExecutionProvider",
  "execution_backend": "Host CPU",
  "precision": "FP32",
  "hardware_npu_active": false,
  "npu_status": "Inactive (Host Development CPU)",
  "runtime_mode": "Development Host (CPU Simulation)",
  "llm_provider": "openrouter-qwen/qwen-2.5-72b-instruct",
  "llm_runs_locally": false,
  "embedding_provider": "onnx-all-MiniLM-L6-v2",
  "embedding_backend": "onnx_minilm",
  "embedding_degraded": false,
  "embedding_degraded_reason": null,
  "retrieval_mode": "semantic-vector",
  "vision_provider": "development-vision-heuristic",
  "external_providers_enabled": true,
  "privacy_checklist": [
    { "item": "Documents stored locally", "status": true, "detail": "Local SQLite database and filesystem storage" },
    { "item": "Embeddings stored locally", "status": true, "detail": "384-d vector embeddings persisted on-device (onnx-all-MiniLM-L6-v2)" },
    { "item": "Vector search local", "status": true, "detail": "Local SQLite exact cosine similarity" },
    { "item": "AI inference local", "status": false, "detail": "Generation is served by the cloud provider openrouter-qwen/qwen-2.5-72b-instruct; embeddings, retrieval and vision stay local" },
    { "item": "No document upload", "status": false, "detail": "Documents are indexed locally, but retrieved excerpts are sent to openrouter-qwen/qwen-2.5-72b-instruct for generation" },
    { "item": "External providers disabled", "status": false, "detail": "External provider opted-in" }
  ]
}
```

> **Expected Snapdragon Mode Telemetry** (after QAIRT inference is implemented and validated; these
> values are a target, not a measurement — no field here may be shown as verified until a physical
> Snapdragon run reports it):
> ```json
> {
>   "runtime_engine": "GenAI Inference Extensions (GenieX/QAIRT)",
>   "active_provider": "QAIRT on QNN",
>   "hardware_npu_active": true,
>   "npu_status": "Hexagon NPU Active (GenAI Inference Extensions)",
>   "llm_provider": "qairt-Qwen3-4B-Instruct-2507",
>   "llm_runs_locally": true,
>   "embedding_provider": "onnx-all-MiniLM-L6-v2",
>   "embedding_backend": "qnn-htp",
>   "retrieval_mode": "semantic-vector",
>   "vision_provider": "onnx-MobileNet-v2"
> }
> ```

The frontend UI strictly enforces:
- **`Hexagon NPU Active`** is rendered with an emerald badge **only** when `hardware_npu_active === true`.
- On the Intel development machine, it renders **`Development Host (CPU Simulation)`** with full telemetry access to inspect providers and benchmark comparisons.
