# ScholarEdge System Architecture

> **Private, On-Device AI Research & Learning Architecture**  
> Designed for heterogeneous execution on Qualcomm Snapdragon Copilot+ PCs with seamless host CPU development support.

---

## 1. High-Level System Architecture

```text
                              ScholarEdge Application (FastAPI + React)
                                             │
        ┌──────────────┬──────────────┬──────┴───────┬──────────────┬──────────────┐
        ▼              ▼              ▼              ▼              ▼              ▼
     Library        Research        Compare         Learn          Vision      Runtime Inspector
   (ingestion)    (grounded RAG)  (extractive)   (LLM + checks)  (pixel stats)   (/api/health)
                                             │
                                Provider Factory Abstraction
                                             │
            ┌────────────────────────────────┼────────────────────────────────┐
            ▼                                ▼                                ▼
   Embedding provider                  LLM provider                    Vision provider
   all-MiniLM-L6-v2                    Qwen3-4B-Instruct-2507          pixel-statistics analysis
                                       (OpenRouter in development)     (MobileNet-v2: scaffolding)
            │                                │                                │
            ▼                                ▼                                ▼
   ONNX Runtime                        QAIRT / GenieX                   CPU (VISION_PROVIDER=development)
   ├─ CPUExecutionProvider  [dev]      (not ONNX Runtime)
   └─ QNNExecutionProvider  [target]   → Hexagon NPU [target; inference not implemented]
      → Hexagon NPU

   Retrieval: exact cosine similarity over SQLite-stored vectors, on the host CPU in both modes.
```

---

## 2. Why Snapdragon for Research AI?

Research AI workloads (PDF document parsing, dense semantic embeddings, multi-paper comparative synthesis, active recall formative generation, and research figure analysis) are the **archetypal workload for private on-device edge computing**:

1. **Data Confidentiality**: Sensitive research and clinical data may be subject to institutional, contractual, or legal restrictions. ScholarEdge's Snapdragon architecture is designed to reduce external data exposure by performing inference locally.
2. **Heterogeneous Compute Architecture**: Modern research analysis combines varied computational profiles:
   - **Hexagon NPU (target)**: embedding generation (MiniLM via QNN) and LLM generation (Qwen3 via QAIRT / GenieX).
   - **Qualcomm Oryon CPU**: PDF parsing, chunking, and exact cosine-similarity retrieval.
   - **Adreno GPU**: renders the browser UI; no ScholarEdge model workload targets it.
3. **All-Day Battery Life & Portability**: Researchers and clinicians need continuous intelligence without tethering to cloud servers or high-wattage desktop GPUs. Snapdragon Copilot+ PCs are designed for sustained low-power on-device inference; ScholarEdge has not yet measured its own power draw on one.

---

## 3. End-to-End Processing Pipelines

### Pipeline A: PDF Ingestion & Semantic Indexing
```text
PDF ──► PyMuPDF text layer ──► Page-aware chunker ──► all-MiniLM-L6-v2 ONNX ──► SQLite (chunks + vectors)
        (no OCR)               (1-based pages,        (384-d, L2-normalised;
                                section labels)        CPU today, QNN/NPU target)
```

### Pipeline B: Grounded RAG
```text
Question ──► MiniLM query embedding ──► Exact cosine retrieval over SQLite (host CPU), top-k
                                                   │
                                     top score >= evidence threshold?
                                     ├── No  ──► "Insufficient evidence in the indexed documents to answer this question."
                                     └── Yes ──► LLM with the grounding prompt
                                                 (OpenRouter in development; Qwen3 via QAIRT / GenieX target)
                                                       │
                                                       ▼
                                                 Answer with citations  [Doc: <title>, Page: <N>]
                                                 └── "View Source Excerpt" opens and highlights the chunk
```

The LLM can still refuse when the retrieved passages do not answer the question; the refusal is
reported as `has_sufficient_evidence: false`.

> **Note:** The LLM targets **GenAI Inference Extensions (GenieX/QAIRT)**, not ONNX Runtime. QAIRT bundle detection and tokenizer loading are implemented, but inference and physical NPU validation are pending. The embedding pipeline targets ONNX Runtime with QNNExecutionProvider.

### Pipeline C: Evidence-Based Comparison (no LLM)
```text
Papers × dimensions ──► per-paper retrieval ──► keep passages that use the dimension's vocabulary
                                                   │
                                  prefer the passage filed under the dimension's usual section
                                                   │
                                                   ▼
                        quoted sentence + page citation, or an explicit evidence gap
Criteria ──► each paper's closest passage + similarity ──► named "better match" only past a 0.05 margin
```

### Pipeline D: Figure Analysis (no LLM)
```text
Figure ──► decode on the host ──► pixel statistics (size, colour, brightness, contrast,
                                   background share, colour count, edge density)
                                        │
                                        ▼
                         rule-based category, no confidence score
                                        │
                     + linked paper ──► retrieved passages with citations
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
  "runtime_engine": "ONNX Runtime (embeddings); pixel statistics (vision, no neural model); cloud API (LLM: openrouter-qwen/qwen-2.5-72b-instruct)",
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
    { "item": "Vector search local", "status": true, "detail": "Exact cosine similarity over SQLite-stored vectors, computed on the host CPU" },
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
>   "vision_provider": "development-vision-heuristic"
> }
> ```

The frontend UI reads this payload and does not assume anything it does not report:
- **`Hexagon NPU Active`** is rendered **only** when `hardware_npu_active === true`.
- On the Intel development machine the header badge reads **`Dev Host (CPU)`**, followed by
  **`Cloud LLM in use`** whenever `llm_runs_locally` is `false`; the Runtime Inspector shows each
  checklist row as green or amber from its `status`.
