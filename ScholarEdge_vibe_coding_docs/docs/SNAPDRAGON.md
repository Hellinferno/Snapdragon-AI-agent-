# ScholarEdge — Snapdragon Deployment Plan & Target Checklist

## Objective

Make ScholarEdge suitable for Snapdragon-powered Windows Copilot+ PCs (Snapdragon X Elite / X Plus with Hexagon NPU 45 TOPS) and validate selected AI workloads on actual target hardware while maintaining full development and test reproducibility on non-Snapdragon host PCs.

---

## Current Status & Verification Boundaries

- **Development Host**: Lenovo ThinkBook 14 G4 IAP (Intel Core i3-1215U, 8 GB RAM, Windows 11 Pro AMD64). Complete 5-studio research-to-learning loop, vector indexing, citation tracking, and 119 automated tests verified.
- **Snapdragon Support**: Implemented as an isolated, pluggable provider layer (`backend/app/providers/qualcomm/`).
- **Development Fallback**: Local zero-weight fallback ensures seamless development on 8 GB RAM without requiring Snapdragon hardware or downloading heavy neural weights.
- **Hardware Claims**: Any claims of Hexagon NPU acceleration are strictly **PENDING TARGET-DEVICE VALIDATION** until the target-device checklist below is executed on physical ARM64 Windows hardware.

---

## Target-Device Checklist

Physical validation on a Snapdragon Windows Copilot+ PC requires recording the following evidence:

| Check | Item | Target Requirement | Evidence Artifact | Status |
|:---:|---|---|---|:---:|
| 1 | **Architecture** | ARM64 Windows 11 (`platform.machine() == 'ARM64'`) | OS / Telemetry probe in benchmark JSON | ⏳ Pending Physical Device |
| 2 | **Model Artifacts** | Qualcomm AI Hub models downloaded to `models/qualcomm/` | SHA-256 hash log | ⏳ Pending Physical Device |
| 3 | **Runtime Engine** | `onnxruntime-qnn` installed on target | `ort.get_available_providers()` containing `QNNExecutionProvider` | ⏳ Pending Physical Device |
| 4 | **QNN Backend** | Qualcomm Hexagon HTP backend (`QnnHtp.dll`) session initialized | QNN provider session initialization logs | ⏳ Pending Physical Device |
| 5 | **NPU Latency** | Cold and warm latency measured on target NPU | Benchmark JSON output in `backend/benchmarks/` | ⏳ Pending Physical Device |
| 6 | **Memory Footprint** | Peak RAM delta and NPU allocation verified under 8 GB ceiling | Tracemalloc memory telemetry | ⏳ Pending Physical Device |
| 7 | **Profiling Output** | QNN operator offload report confirming Hexagon NPU acceleration | Execution profiling log | ⏳ Pending Physical Device |

---

## Deployment Architecture

```text
ScholarEdge Application (FastAPI + React)
        ↓
Provider Factory (`backend/app/providers/factory.py`)
        ↓
Qualcomm Provider Layer (`backend/app/providers/qualcomm/`)
  ├── QualcommEmbeddingProvider (all-MiniLM-L6-v2, 384-d)
  ├── QualcommLLMProvider (Qwen3-4B-Instruct-2507, QAIRT target)
  └── QualcommVisionProvider (MobileNet-v2 / CLIP)
        ↓
ONNX Runtime with QNN Execution Provider (`QnnHtp.dll` on Hexagon NPU) for embedding and vision
GenAI Inference Extensions (QAIRT) for the LLM; inference validation pending
        ↓
Target Hardware (Snapdragon X Elite / Copilot+ PC)
```

---

## Qualcomm AI Hub Candidate Models

These models are designated candidates for target-device deployment via Qualcomm AI Hub:

| Modality | Candidate Model | Target Precision | NPU Runtime Target |
|---|---|---|---|
| **Embeddings** | `all-MiniLM-L6-v2` | INT8 / FP16 | ONNX Runtime + QNN HTP |
| **Grounded LLM** | `Qwen3-4B-Instruct-2507` | INT4 (W4A16) | GenAI Inference Extensions / QAIRT (pending validation) |
| **Vision / Figures** | `MobileNet-v2` / `CLIP-ViT-B-32` | INT8 / FP16 | ONNX Runtime + QNN HTP |
| **OCR** | `EasyOCR` / `TrOCR` | INT8 | ONNX Runtime + QNN HTP |

---

## Target Environment Setup

To deploy on a physical Snapdragon Windows Copilot+ PC:

```powershell
# 1. Clone repository on ARM64 Windows machine
git clone https://github.com/Hellinferno/Snapdragon-AI-agent-.git
cd Snapdragon-AI-agent-/backend

# 2. Set up ARM64 Python environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install onnxruntime-qnn

# 3. Configure Qualcomm Hexagon SDK runtime path
$env:PATH += ";C:\Program Files\Qualcomm\Hexagon_SDK\lib\hexagon_nn_skel"

# 4. Run ScholarEdge with Qualcomm backend
$env:PROVIDER_BACKEND = "qualcomm"
$env:QUALCOMM_DEVICE_TARGET = "Snapdragon X Elite"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Reproducible Benchmark Harness

Run the automated benchmark harness:

```powershell
# From backend directory:
python scripts/benchmark_snapdragon.py --dry-run
```

On a non-Snapdragon machine, the harness automatically labels the run as `DEVELOPMENT_HOST_SIMULATION` with `hardware_npu_verified: false` and `PENDING_TARGET_DEVICE_VALIDATION`. When run on a Snapdragon machine with QNN active, it records empirical NPU metrics to `backend/benchmarks/snapdragon_benchmark_<timestamp>.json`.
