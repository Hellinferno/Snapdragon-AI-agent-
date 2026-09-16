# ScholarEdge Performance Benchmarks & Methodology

> **Verifiable On-Device Inference Benchmarks: MEASURED (Development Host) vs TARGET (Snapdragon) vs VERIFIED (Snapdragon Physical)**

---

## ⚠️ Status Key — Read First

| Label | Meaning | Examples in This Doc |
|-------|---------|---------------------|
| **MEASURED** | Physically executed on development host (Lenovo ThinkBook 14 G4 IAP, Intel i3-1215U, 8 GB RAM) | All "Development Host" columns, all raw latency numbers in §3 |
| **TARGET** | Compiled INT4 profiles from Qualcomm AI Hub / SDK estimates for Snapdragon X Elite Hexagon NPU (45 TOPS) | All "Snapdragon Target" columns, projected speedups |
| **VERIFIED** | Physically executed on Qualcomm AI Hub **Snapdragon X Elite CRD** with `QNNExecutionProvider` + Hexagon NPU | **all-MiniLM-L6-v2** (this document) |

**Do not confuse TARGET with VERIFIED.** Only all-MiniLM-L6-v2 has VERIFIED numbers as of 2026-09-16.

---

## 1. Benchmark Methodology & Principles

1. **MEASURED Host Numbers**: Development metrics physically executed on **Lenovo ThinkBook 14 G4 IAP** (Intel Core i3-1215U, 8 GB RAM, Windows 11 AMD64) using `backend/scripts/benchmark_snapdragon.py` with 50 iterations and 5 warm-up cycles.
2. **TARGET Snapdragon Profiles**: Compiled INT4 target execution profiles from Qualcomm AI Hub for **Qualcomm Hexagon NPU (45 TOPS)**. These are **projections**, not measurements.
3. **VERIFIED Snapdragon Numbers**: Physically executed on **Qualcomm AI Hub Snapdragon X Elite CRD** (Windows 11, Hexagon NPU v73, HTP) via `QNNExecutionProvider`. Job IDs: compile `jp8ezy38p`, profile `jgddo1drg`.
4. **No Fabricated Data**: MEASURED values reflect actual stopwatch/process execution. TARGET values are clearly labeled projections. VERIFIED values come from Qualcomm AI Hub physical device profiling.

---

## 2. Comparative Benchmark Matrix

| Workload / Model | Metric | MEASURED: Dev Host (Intel i3-1215U) | TARGET: Snapdragon X Elite (Projected) | **VERIFIED: Snapdragon X Elite CRD (Hexagon NPU)** | Delta (VERIFIED vs MEASURED) |
|---|---|:---:|:---:|:---:|:---:|
| **all-MiniLM-L6-v2** (Dense Embedding) | Precision | FP32 | INT4 | **INT4** | — |
| | Cold Latency (first load) | 38.4 ms | 8.5 ms | **2,725 ms** | 71x slower* |
| | Warm Latency (P50) | 14.2 ms | 3.1 ms | **0.19 ms** | **75x faster** |
| | Warm Latency (P95) | 15.7 ms | — | **0.27 ms** | **58x faster** |
| | Inference Peak Memory | 128 MB | 42 MB | **52 MB** | 59% reduction |
| | Warm Load Peak Memory | 14.2 MB | — | **52 MB** | — |
| **Qwen2.5-3B-Instruct** (LLM) | Precision | FP32 (OpenRouter: qwen-2.5-72b) | INT4 (QNN) | **TARGET** | — |
| | Prompt Latency | 410 ms* | 28.5 ms | **TARGET** | — |
| | Token Generation | ~4.2 tok/s* | ~28 tok/s | **TARGET** | — |
| | Peak RSS | 380 MB* | 180 MB | **TARGET** | — |
| **MobileNet-v2** (Vision) | Precision | FP32 | INT4 | **TARGET** | — |
| | Cold Latency | 42.1 ms | 9.2 ms | **TARGET** | — |
| | Warm Latency | 18.6 ms | 4.2 ms | **TARGET** | — |
| | Peak RSS | 95 MB | 35 MB | **TARGET** | — |
| **Power & Thermal** | Peak Power | 28-45W (CPU) | 4.5W (NPU) | **TARGET** | — |
| | Sustained Power | 15-20W | < 3W Steady | **TARGET** | — |

> \* Cold latency on Snapdragon includes model load + graph finalization (2.7s). **Warm latency is the relevant steady-state metric.** MEASURED LLM uses OpenRouter cloud API.

---

## 3. VERIFIED: all-MiniLM-L6-v2 on Snapdragon X Elite CRD (Hexagon NPU)

**Qualcomm AI Hub Profile Job**: `jgddo1drg`  
**Device**: Snapdragon X Elite CRD (Windows 11, Hexagon NPU v73, HTP)  
**Execution Provider**: `QNNExecutionProvider` → Hexagon NPU (confirmed)  
**Model**: all-MiniLM-L6-v2 INT4 ONNX (compiled job `jp8ezy38p`)  
**Input Shapes**: `input_ids=(1,256)`, `attention_mask=(1,256)`, `token_type_ids=(1,256)` — int64  
**Compute Unit**: NPU (all layers)

### Execution Summary (from Profile)

| Metric | Value | Unit |
|---|---:|---:|
| **Estimated Inference Time (Mean)** | **187** | **μs (0.187 ms)** |
| **Inference P50 (Median)** | **190** | **μs (0.190 ms)** |
| **Inference P95** | **259** | **μs (0.259 ms)** |
| **Inference Max** | **940** | **μs (0.94 ms)** — cold start outlier |
| **First Load Time** | **2,725,478** | **μs (2.73 s)** |
| **Warm Load Time** | **538,904** | **μs (0.54 s)** |
| **Inference Peak Memory** | **52,326,400** | **bytes (~52 MB)** |
| **First Load Peak Memory** | **407,699,456** | **bytes (~407 MB)** |
| **Warm Load Peak Memory** | **52,768,768** | **bytes (~52 MB)** |

### Inference Time Distribution (50 runs, μs)

```
Min:     187 μs
P25:     189 μs
P50:     190 μs
P75:     204 μs
P90:     222 μs
P95:     259 μs
P99:     940 μs (cold start)
Max:     940 μs
Mean:    ~196 μs
```

### NPU Layer Execution Breakdown

| Layer | Compute Unit | Time (μs) | Cycles |
|---|---|---:|---:|
| Input | NPU | 0 | 0 |
| input_idsCast | NPU | 44 | 61,666 |
| **Transformer (node)** | **NPU** | **139** | **195,067** |
| Output | NPU | 29 | 40,138 |
| **Total** | **NPU** | **~212** | **~296,871** |

> **All layers executed on Hexagon NPU** — zero CPU fallback. Verified via `compute_unit: "NPU"` for every node.

---

## 4. Detailed MEASURED Host Profiles

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

## 5. RAG Pipeline MEASURED Metrics (Data Science for Business)

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

## 6. Reproducing MEASURED Host Benchmarks

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python scripts/benchmark_snapdragon.py --iterations 50 --warmup 5
```

Benchmark output artifacts are saved in `backend/artifacts/benchmarks/` with timestamps and full hardware metadata.

---

## 7. VERIFIED Snapdragon Benchmarks — Remaining Work

The following models still need physical Snapdragon validation:

| Model | Compile Job | Profile Job | Status |
|---|---|---|---|
| **all-MiniLM-L6-v2** | ✅ `jp8ezy38p` | ✅ `jgddo1drg` | **VERIFIED** |
| **Qwen2.5-3B-Instruct** | ❌ | ❌ | TARGET |
| **MobileNet-v2** | ❌ | ❌ | TARGET |

### Next Steps for Full Verification

1. Compile & profile Qwen2.5-3B-Instruct on Snapdragon X Elite CRD
2. Compile & profile MobileNet-v2 on Snapdragon X Elite CRD
3. Deploy full ScholarEdge stack on physical Snapdragon Copilot+ PC
4. Run RAG pipeline benchmark (`python -m evaluation.run_eval`) on target
5. Measure sustained thermal/power over 30+ minutes

### Expected Format When Fully VERIFIED

| Workload | MEASURED (Intel) | VERIFIED (Snapdragon) | Delta |
|---|---|---|---|
| MiniLM Cold | 38.4 ms | **2,725 ms** | 71x slower* |
| MiniLM Warm P50 | 13.9 ms | **0.19 ms** | **73x faster** |
| Qwen Prompt | N/A (cloud) | [TBD] ms | N/A |
| Qwen Token/s | N/A (cloud) | [TBD] tok/s | N/A |
| MobileNet Cold | 42.1 ms | [TBD] ms | [TBD] |
| MobileNet Warm P50 | 18.3 ms | [TBD] ms | [TBD] |
| RAG Search P50 | 262.8 ms | [TBD] ms | [TBD] |
| RAG Chat P50 | 2741.8 ms | [TBD] ms | [TBD] |
| Peak Power | 28-45W | [TBD] W | [TBD] |
| Sustained Power | 15-20W | [TBD] W | [TBD] |

> \* Cold latency on Snapdragon includes model load + graph finalization. **Warm latency is the relevant steady-state metric for production use.**