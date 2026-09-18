# Snapdragon Copilot+ PC Deployment Guide

> **Deploying ScholarEdge on Qualcomm Snapdragon X Elite with Hexagon NPU**
>
> ⚠️ **STATUS: ARCHITECTURE IMPLEMENTED — PHYSICAL VALIDATION PENDING**

---

## 1. Qualcomm Snapdragon Hardware Architecture

ScholarEdge targets the **Qualcomm Snapdragon X Elite** (and Snapdragon X Plus) platform:

- **Hexagon NPU**: Delivering **45 TOPS** of dedicated neural compute for INT4 and INT8 matrix operations.
- **Qualcomm Neural Network (QNN) SDK**: Provides direct hardware offload to the Hexagon Tensor Processor (HTP) through `QnnHtp.dll`.
- **ONNX Runtime QNN Execution Provider**: Enables direct execution of quantized ONNX models on the Hexagon NPU with minimal CPU host overhead.
- **GenAI Inference Extensions (GenieX/QAIRT)**: Qualcomm's runtime for LLM inference on Hexagon NPU, used by Qwen3-4B-Instruct-2507.

```text
┌──────────────────────────────────────────────────────────────┐
│                    ScholarEdge Architecture                  │
├──────────────────────────────────────────────────────────────┤
│ Application Layer (FastAPI + React 5-Studio Suite)           │
├──────────────────────────────────────────────────────────────┤
│ ONNX Runtime (v1.20+)                                         │
│   ├── QNNExecutionProvider (Embedding/Vision)                │
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

> **Architecture Note**: The LLM (Qwen3-4B-Instruct-2507) runs via **GenAI Inference Extensions (GenieX/QAIRT)** on the Hexagon NPU, while Embedding (MiniLM) and Vision (MobileNet) use ONNX Runtime with QNNExecutionProvider.

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

Edit `backend/.env`:

```ini
AI_PROVIDER=qualcomm
QUALCOMM_PREFERRED_PROVIDER=QNNExecutionProvider
QUALCOMM_FALLBACK_PROVIDER=CPUExecutionProvider
QUALCOMM_QNN_BACKEND_PATH=QnnHtp.dll
QUALCOMM_HTP_PERFORMANCE_MODE=burst
QUALCOMM_HTP_GRAPH_OPTIMIZATION=3
QUALCOMM_PRECISION=int4
QUALCOMM_LLM_RUNTIME=geniex_qairt
```

---

## 3. Physical Validation & Benchmark Execution

⚠️ **This section documents the procedure. No physical validation has been performed yet.**

To execute the physical validation harness on your Snapdragon device:

```powershell
# Activate backend environment
cd backend
.\.venv\Scripts\Activate.ps1

# Run the benchmark harness
python scripts/benchmark_snapdragon.py --iterations 50 --warmup 5
```

The benchmark script records:
- **Provider Resolution**: Confirms `QNNExecutionProvider` loaded.
- **Cold vs Warm Latency**: Initial graph compilation vs steady-state NPU inference.
- **P50 / P95 Latency**: Statistical distribution across 50 iterations.
- **Peak RSS**: Confirms memory consumption remains well within bounds.
- **Artifact Generation**: Saves execution results to `backend/artifacts/benchmarks/`.

---

## 4. Physical Validation Checklist (Must Complete Before Claiming VERIFIED)

- [ ] Snapdragon X Elite Copilot+ PC acquired and running Windows 11 ARM64
- [ ] Qualcomm QNN SDK v2.28+ installed with `QnnHtp.dll` in PATH
- [ ] `onnxruntime-qnn` installed in Python environment
- [ ] `AI_PROVIDER=qualcomm` configured in `.env`
- [ ] Application starts without errors (`uvicorn app.main:app --reload`)
- [ ] `/api/health` returns `"hardware_provider": "qualcomm"` and `"hardware_npu_active": true`
- [ ] `ort.get_available_providers()` includes `QNNExecutionProvider`
- [ ] All 3 models (MiniLM, Qwen, MobileNet) load without OOM on 16GB+ RAM
- [ ] `benchmark_snapdragon.py` completes 50 iterations successfully
- [ ] Benchmark artifacts saved to `backend/artifacts/benchmarks/`
- [ ] RAG evaluation (`python -m evaluation.run_eval`) passes on target
- [ ] Thermal/power sustained for 30+ minutes without throttling
- [ ] **VERIFIED metrics recorded in BENCHMARKS.md**

---

## 5. Current Implementation Status

| Component | Code Status | Physical Validation |
|---|---|---|
| `QNNExecutionProvider` factory (Embedding/Vision) | ✅ Implemented | ❌ Pending |
| GenAI Inference Extensions (GenieX/QAIRT) factory | ✅ Implemented | ❌ Pending |
| Model ONNX export (MiniLM, Qwen3-4B, MobileNet) | ✅ Implemented | ❌ Pending |
| QAIRT bundle download & verification | ✅ Implemented | ❌ Pending |
| INT4 quantization configs | ✅ Implemented | ❌ Pending |
| Provider isolation (no fallback to CPU) | ✅ Implemented | ❌ Pending |
| Benchmark harness | ✅ Implemented | ❌ Pending |
| Hardware telemetry API | ✅ Implemented | ❌ Pending |
| RAG pipeline end-to-end | ✅ Implemented | ❌ Pending |

**Do not claim Snapdragon NPU execution until all checkboxes in Section 4 are complete.**

> **Current Status**: MiniLM & MobileNet models are VERIFIED on Snapdragon X Elite CRD via QNNExecutionProvider. Qwen3-4B-Instruct-2507 QAIRT bundle is downloaded and provider integration complete; NPU validation pending GenieX/QAIRT on Snapdragon X Elite CRD.