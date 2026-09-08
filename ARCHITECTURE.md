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
      (all-MiniLM-L6-v2)              (Qwen2.5-3B-Instruct)              (MobileNet-v2)
               │                               │                               │
               └───────────────────────────────┼───────────────────────────────┘
                                               ▼
                                      ONNX Runtime Engine
                                 (ort.InferenceSession v1.20+)
                                               │
                     ┌─────────────────────────┴─────────────────────────┐
                     ▼                                                   ▼
            [TARGET ACCELERATOR]                                 [DEVELOPMENT HOST]
           QNNExecutionProvider                                 CPUExecutionProvider
                     │                                                   │
                     ▼                                                   ▼
          Qualcomm Hexagon HTP NPU                              Host CPU / Intel i3
              (45 TOPS INT4)                                     (FP32 Simulation)
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
                                    └── Yes ──► Qwen2.5-3B ONNX Forward Pass
                                                      │
                                                      ▼
                                                Claim-Level Verification
                                                      │
                                                      ▼
                                    Answer with Verifiable Citations
                                    [Paper: X, Page: Y, Section: Z, Chunk: N]
                                    └── "View Source Excerpt" modal jump
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

ScholarEdge maintains continuous hardware telemetry via `/api/health` and `/api/runtime/status`:

```json
{
  "status": "healthy",
  "runtime_engine": "ONNX Runtime",
  "execution_provider": "CPUExecutionProvider",
  "hardware_npu_active": false,
  "npu_status": "Inactive (Host Development CPU)",
  "host_device": "Windows AMD64",
  "host_architecture": "AMD64",
  "privacy_mode": "Strict Local-First",
  "privacy_checklist": [
    { "item": "Documents stored locally", "verified": true },
    { "item": "Embeddings stored locally", "verified": true },
    { "item": "Vector search local", "verified": true },
    { "item": "AI inference local", "verified": true },
    { "item": "No document upload", "verified": true },
    { "item": "External providers disabled", "verified": true }
  ]
}
```

The frontend UI strictly enforces:
- **`Hexagon NPU Active`** is rendered with an emerald badge **only** when `hardware_npu_active === true`.
- On the Intel development machine, it renders **`Development Host (CPU Simulation)`** with full telemetry access to inspect providers and benchmark comparisons.
