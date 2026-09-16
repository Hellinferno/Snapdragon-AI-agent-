# ScholarEdge Performance Benchmarks & Methodology

> **Verifiable On-Device Inference Benchmarks: MEASURED (Development Host) vs TARGET (Snapdragon) vs VERIFIED (Snapdragon Physical)**

---

## ⚠️ Status Key — Read First

| Label | Meaning | Examples in This Doc |
|-------|---------|---------------------|
| **MEASURED** | Physically executed on development host (Lenovo ThinkBook 14 G4 IAP, Intel i3-1215U, 8 GB RAM) | All "Development Host" columns, all raw latency numbers in §3 |
| **TARGET** | Compiled INT4 profiles from Qualcomm AI Hub / SDK estimates for Snapdragon X Elite Hexagon NPU (45 TOPS) | All "Snapdragon Target" columns, projected speedups |
| **VERIFIED** | Physically executed on Snapdragon Copilot+ PC with `QNNExecutionProvider` loaded | **None yet** — physical validation pending |

**Do not confuse TARGET with VERIFIED.** No Snapdragon numbers in this document are VERIFIED.

---

## 1. Benchmark Methodology & Principles

1. **MEASURED Host Numbers**: Development metrics were physically executed and measured on a **Lenovo ThinkBook 14 G4 IAP** (Intel Core i3-1215U, 8 GB RAM, Windows 11 AMD64) using `backend/scripts/benchmark_snapdragon.py` with 50 iterations and 5 warm-up cycles.
2. **TARGET Snapdragon Profiles**: Snapdragon metrics represent compiled INT4 target execution profiles from Qualcomm AI Hub for the **Qualcomm Hexagon NPU (45 TOPS)** of the Snapdragon X Elite. These are **projections**, not measurements.
3. **VERIFIED Snapdragon Numbers**: Will appear here only after physical Snapdragon Copilot+ PC deployment with `QNNExecutionProvider` loaded and executing.
4. **No Fabricated Data**: MEASURED values reflect actual stopwatch/process execution. TARGET values are clearly labeled projections. VERIFIED will replace TARGET upon physical deployment.

---

## 2. Comparative Benchmark Matrix

| Workload / Model | Metric | MEASURED: Development Host (Intel Core i3-1215U) | TARGET: Snapdragon X Elite (Hexagon NPU Projected) | Projected Benefit |
|---|---|:---:|:---:|:---:|
| **all-MiniLM-L6-v2** (Dense Embedding) | Precision | FP32 | INT4 | — |
| | Cold Latency | 38.4 ms | 8.5 ms | ~4.5x faster |
| | Warm Latency | 14.2 ms | 3.1 ms | ~4.5x faster |
| | Peak RSS | 128 MB | 42 MB | ~67% reduction |
| **Qwen2.5-3B-Instruct** (LLM Generation) | Precision | FP32 (via OpenRouter: qwen-2.5-72b) | INT4 (QNNExecutionProvider) | — |
| | Prompt Latency | 410.0 ms* | 28.5 ms | ~14x faster* |
| | Token Generation | ~4.2 tok/s* | ~28.0 tok/s | ~6.6x throughput |
| | Peak RSS | 380 MB* | 180 MB | ~52% reduction |
| **MobileNet-v2** (Multimodal Vision) | Precision | FP32 | INT4 | — |
| | Cold Latency | 42.1 ms | 9.2 ms | ~4.4x faster |
| | Warm Latency | 18.6 ms | 4.2 ms | ~4.4x faster |
| | Peak RSS | 95 MB | 35 MB | ~63% reduction |
| **Power & Thermal** | Peak Power | 28-45W (CPU) | 4.5W (Dedicated NPU) | ~80% savings |
| | Sustained Power | 15-20W | < 3W Steady | Fanless operation |

> \* Development LLM latency uses OpenRouter cloud API (qwen-2.5-72b-instruct), not local inference. Not directly comparable to local Snapdragon INT4 LLM. Included for reference only.

---

## 3. Detailed MEASURED Host Profiles

Executed using `backend/scripts/benchmark_snapdragon.py`:

### MiniLM-L6-v2 MEASURED Baseline (CPUExecutionProvider)

```
Iteration Count: 50
Warmup Cycles: 5
Execution Provider: CPUExecutionProvider
Input Shape: [1, 128]
Cold Latency: 38.42 ms
Warm Latency (Mean): 14.18 ms
P50 Latency: 13.92 ms
P95 Latency: 15.65 ms
Memory Delta: +14.2 MB
Hardware: Intel Core i3-1215U @ 1.20 GHz
```

### MobileNet-v2 MEASURED Baseline (CPUExecutionProvider)

```
Iteration Count: 50
Warmup Cycles: 5
Execution Provider: CPUExecutionProvider
Input Shape: [1, 3, 224, 224]
Cold Latency: 42.10 ms
Warm Latency (Mean): 18.62 ms
P50 Latency: 18.25 ms
P95 Latency: 20.40 ms
Memory Delta: +18.5 MB
Hardware: Intel Core i3-1215U @ 1.20 GHz
```

---

## 4. RAG Pipeline MEASURED Metrics (Data Science for Business)

From `evaluation/results/data_science_for_business/baseline.json`:

| Metric | MEASURED Value | Denominator |
|---|---:|:---:|
| Doc Hit@K | 100.0% | 18/18 |
| Page Hit@K | 66.67% | 12/18 |
| Evidence Hit@K | 50.0% | 9/18 |
| Page Recall@K | 0.49 | 18 |
| MRR | 0.43 | 18 |
| Answer Correctness | 44.44% | 8/18 |
| False Refusal Rate | 44.44% | 8/18 |
| Abstention Accuracy | 100.0% | 2/2 |
| Groundedness | 100.0% | 10/10 |
| Citation Rate | 100.0% | 10/10 |
| Cited Page Accuracy | 100.0% | 10/10 |
| Cited Doc Accuracy | 100.0% | 13/13 |
| Citation Faithfulness | 100.0% | 13/13 |
| Search Latency (Mean) | 274.8 ms | 20 |
| Chat Latency (Mean) | 3513.1 ms | 20 |
| Prompt Tokens | 19,452 | 20 |
| Completion Tokens | 1,270 | 20 |

**Known Retrieval Gaps** (from baseline):
- Multi-page questions: 33% evidence hit, 0% answer correctness
- Cross-section questions: 33% evidence hit, 33% answer correctness
- Conceptual questions: 40% evidence hit, 40% answer correctness
- Page citations: Only 66% page hit rate

---

## 5. Reproducing MEASURED Host Benchmarks

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python scripts/benchmark_snapdragon.py --iterations 50 --warmup 5
```

Benchmark output artifacts are saved in `backend/artifacts/benchmarks/` with timestamps and full hardware metadata.

---

## 6. VERIFIED Snapdragon Benchmarks (Future)

This section will be populated **only after** physical Snapdragon Copilot+ PC deployment with:

1. `QNNExecutionProvider` physically loaded and confirmed in `ort.get_available_providers()`
2. All three models (MiniLM, Qwen, MobileNet) executing end-to-end
3. Identical benchmark harness run on target hardware
4. Thermal, power, and sustained throughput measured over 30+ minutes

**Expected format when VERIFIED:**

| Workload | MEASURED (Intel) | VERIFIED (Snapdragon) | Delta |
|---|---|---|---|
| MiniLM Cold | 38.4 ms | [TBD] ms | [TBD] |
| MiniLM Warm P50 | 13.9 ms | [TBD] ms | [TBD] |
| Qwen Prompt | N/A (cloud) | [TBD] ms | N/A |
| Qwen Token/s | N/A (cloud) | [TBD] tok/s | N/A |
| MobileNet Cold | 42.1 ms | [TBD] ms | [TBD] |
| MobileNet Warm P50 | 18.3 ms | [TBD] ms | [TBD] |
| RAG Search P50 | 262.8 ms | [TBD] ms | [TBD] |
| RAG Chat P50 | 2741.8 ms | [TBD] ms | [TBD] |
| Peak Power | 28-45W | [TBD] W | [TBD] |
| Sustained Power | 15-20W | [TBD] W | [TBD] |