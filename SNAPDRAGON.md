# Snapdragon Copilot+ PC Deployment Guide

> **Deploying ScholarEdge on Qualcomm Snapdragon X Elite with Hexagon NPU**
>
> ⚠️ **STATUS: TARGET DEPLOYMENT — PHYSICAL VALIDATION PENDING**
>
> **Qwen3-4B-Instruct-2507 → QAIRT/GenieX → Hexagon NPU (planned; Snapdragon hardware validation pending).**
>
> During development, LLM generation uses the **OpenRouter** cloud API on an Intel host. Nothing in this
> guide has been executed on Snapdragon hardware yet.

---

## 0. Verified vs Target vs Not Yet Verified

### ✅ Verified (development host)

```text
Lenovo ThinkBook 14 G4 IAP · Intel Core i3-1215U · 8 GB RAM · Windows 11 · AMD64
ONNX Runtime CPUExecutionProvider (all-MiniLM-L6-v2 embeddings)
125 hermetic tests · RAG evaluation · frontend build
Complete application workflow: Library → Research → Compare → Learn → Vision → Runtime Inspector
```

### 🎯 Target architecture

```text
Snapdragon X Elite
        ↓
Hexagon NPU
        ↓
QNN (ONNX Runtime QNNExecutionProvider)
        ↓
all-MiniLM-L6-v2 embeddings

Qwen3-4B-Instruct-2507
        ↓
QAIRT / GenieX            (planned; generation not implemented)
        ↓
Hexagon NPU               (Snapdragon hardware validation pending)
```

Until then, development builds generate text through **OpenRouter** (cloud API); see PRIVACY.md.

Retrieval (cosine similarity over SQLite vectors) runs on the CPU in this design; the NPU computes
embeddings, not the vector search.

### ❌ Not yet verified

```text
Physical Snapdragon execution
Qwen3 QAIRT generation (bundle detected and tokenizer loads; inference not implemented)
NPU latency · tokens/sec · power consumption
Air-gapped physical test
Figure classification on the NPU (MobileNet-v2 path is scaffolding; no trained figure classifier)
```

---

## 1. Qualcomm Snapdragon Hardware Architecture

ScholarEdge targets the **Qualcomm Snapdragon X Elite** (and Snapdragon X Plus) platform:

- **Hexagon NPU**: Delivering **45 TOPS** of dedicated neural compute for INT4 and INT8 matrix operations.
- **Qualcomm Neural Network (QNN) SDK**: Provides direct hardware offload to the Hexagon Tensor Processor (HTP) through `QnnHtp.dll`.
- **ONNX Runtime QNN Execution Provider**: Enables direct execution of quantized ONNX models on the Hexagon NPU with minimal CPU host overhead.
- **GenAI Inference Extensions (GenieX/QAIRT)**: Qualcomm's runtime for LLM inference on Hexagon NPU, planned for Qwen3-4B-Instruct-2507 (generation not yet implemented).

```text
┌──────────────────────────────────────────────────────────────┐
│                    ScholarEdge Architecture                  │
├──────────────────────────────────────────────────────────────┤
│ Application Layer (FastAPI + React 5-Studio Suite)           │
├──────────────────────────────────────────────────────────────┤
│ ONNX Runtime (v1.20+)                                         │
│   ├── QNNExecutionProvider (Embeddings)                      │
│   └── CPUExecutionProvider (Development Host Fallback)       │
├──────────────────────────────────────────────────────────────┤
│ GenAI Inference Extensions (GenieX/QAIRT)                     │
│   ├── GenieX Runtime                                         │
│   └── QAIRT Runtime                                          │
├──────────────────────────────────────────────────────────────┤
│ Qualcomm QNN Backend                                         │
│   ├── QnnHtp.dll (Hexagon Tensor Processor)                 │
│   └── QnnSystem.dll (System / Context Manager)              │
├──────────────────────────────────────────────────────────────┤
│ Snapdragon Hardware Silicon                                  │
│   ├── Hexagon NPU (45 TOPS Matrix Accelerator)              │
│   ├── 12-Core Qualcomm Oryon CPU                            │
│   └── Qualcomm Adreno GPU                                    │
└──────────────────────────────────────────────────────────────┘
```

> **Architecture Note**: The LLM target is Qwen3-4B-Instruct-2507 via **GenAI Inference Extensions (GenieX/QAIRT)**. The bundle and tokenizer are detected, but QAIRT inference and physical NPU validation are pending. Embeddings (MiniLM) use ONNX Runtime with QNNExecutionProvider. The Qwen3 bundle is not converted to ONNX. A MobileNet-v2 vision provider exists as scaffolding only: there is no trained figure classifier, so figure analysis currently runs as pixel statistics on the CPU.

---

## 2. Environment Configuration on Snapdragon PC

On a Snapdragon X Elite Copilot+ PC running Windows 11 on ARM (Build 26100+):

### 1. Install Qualcomm Neural Processing SDK

Ensure Qualcomm QNN SDK v2.28+ is installed and the HTP runtime binaries are present in the system PATH:

```powershell
# Verify QnnHtp.dll availability
Get-Command QnnHtp.dll -ErrorAction SilentlyContinue
```

### 2. Install Python ARM64 & Dependencies

```powershell
# Ensure ARM64 native Python 3.11/3.12 is used
python -c "import platform; print(platform.machine())"  # Outputs: ARM64

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install onnxruntime-qnn
```

### 3. Configure Runtime Environment (.env)

Edit `backend/.env` (these are the settings `app/core/config.py` actually reads):

```ini
PROVIDER_BACKEND=qualcomm
LLM_PROVIDER=qualcomm
EMBEDDING_PROVIDER=qualcomm
VISION_PROVIDER=development
ALLOW_EXTERNAL_PROVIDERS=false
QUALCOMM_DEVICE_TARGET=auto
QUALCOMM_BACKEND_PATH=QnnHtp.dll
QUALCOMM_PERFORMANCE_MODE=burst
# optional overrides
# QUALCOMM_MODEL_DIR=backend/models/qualcomm
# QUALCOMM_QAIRT_DIR=<path to the Qwen3-4B-Instruct-2507 QAIRT bundle>
```

Also set `VISION_PROVIDER=development`: otherwise it inherits `PROVIDER_BACKEND=qualcomm`, and the
Qualcomm vision provider has no trained figure classifier to load.

---

## 3. Physical Validation & Benchmark Execution

⚠️ **This section documents the procedure. No physical validation has been performed yet.**

To execute the physical validation harness on your Snapdragon device:

```powershell
# Activate backend environment
cd backend
.\.venv\Scripts\Activate.ps1

# Run the benchmark harness (add --dry-run for a quick verification pass)
python scripts/benchmark_snapdragon.py --output-dir benchmarks
```

The benchmark script records:
- **Provider Resolution**: Confirms `QNNExecutionProvider` loaded.
- **Cold vs Warm Latency**: Initial graph compilation vs steady-state NPU inference.
- **P50 / P95 Latency**: Statistical distribution across the harness's iterations.
- **Peak RSS**: Confirms memory consumption remains well within bounds.
- **Artifact Generation**: Saves execution results to `backend/benchmarks/` (or `--output-dir`).

---

## 4. Physical Validation Checklist (Must Complete Before Claiming VERIFIED)

- [ ] Snapdragon X Elite Copilot+ PC acquired and running Windows 11 ARM64
- [ ] Qualcomm QNN SDK v2.28+ installed with `QnnHtp.dll` in PATH
- [ ] `onnxruntime-qnn` installed in Python environment
- [ ] `PROVIDER_BACKEND=qualcomm` (and `LLM_PROVIDER` / `EMBEDDING_PROVIDER`) configured in `.env`
- [ ] Application starts without errors (`uvicorn app.main:app --reload`)
- [ ] `/api/health` returns `"provider_backend": "qualcomm"`, `"active_provider": "QNNExecutionProvider"` and `"hardware_npu_active": true`
- [ ] `ort.get_available_providers()` includes `QNNExecutionProvider`
- [ ] MiniLM (ONNX/QNN) and Qwen3 (QAIRT) load without OOM on 16GB+ RAM
- [ ] QAIRT generation implemented and producing grounded, cited answers on the device
- [ ] Air-gapped test in PRIVACY.md §5 passes with the network disconnected
- [ ] `benchmark_snapdragon.py` completes successfully on the device
- [ ] Benchmark artifacts saved to `backend/benchmarks/`
- [ ] RAG evaluation (`python -m evaluation.run_eval`) passes on target
- [ ] Thermal/power sustained for 30+ minutes without throttling
- [ ] **VERIFIED metrics recorded in BENCHMARKS.md**

---

## 5. Current Implementation Status

| Component | Code Status | Physical Validation |
|---|---|---|
| `QNNExecutionProvider` factory (embeddings) | ✅ Implemented | ❌ Pending |
| QAIRT / GenieX LLM provider | ⚠️ Scaffolding only: bundle detection and tokenizer loading; no generation | ❌ Pending |
| MiniLM ONNX artifact | ✅ Download & verification script | ❌ Pending |
| Figure classifier for the vision provider | ❌ Not trained (MobileNet-v2 provider is scaffolding) | ❌ Pending |
| QAIRT generation (Qwen3 inference) | ❌ Not implemented | ❌ Pending |
| QAIRT LLM bundle (Qwen3-4B-Instruct-2507) | ✅ Detected; tokenizer loaded | ❌ Inference and validation pending |
| QAIRT bundle download & verification | ✅ Implemented | ❌ Pending |
| INT4 quantization configs | ✅ Implemented | ❌ Pending |
| Provider isolation (no fallback to CPU) | ✅ Implemented | ❌ Pending |
| Benchmark harness | ✅ Implemented | ❌ Pending |
| Hardware telemetry API | ✅ Implemented | ❌ Pending |
| RAG pipeline end-to-end | ✅ Development mode (OpenRouter generation); ❌ Snapdragon mode blocked on QAIRT generation | ❌ Pending |

**Do not claim Snapdragon NPU execution until all checkboxes in Section 4 are complete.**

> **Current Status**: The Qwen3-4B-Instruct-2507 QAIRT bundle is present, the tokenizer loads, and the provider reports that inference is unavailable. Do not claim Snapdragon NPU execution or publish NPU benchmark values until QAIRT generation succeeds on physical target hardware.
