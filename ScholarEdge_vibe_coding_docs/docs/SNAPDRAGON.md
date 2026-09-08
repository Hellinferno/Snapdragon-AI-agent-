# ScholarEdge — Snapdragon Deployment Plan

## Objective

Make ScholarEdge suitable for Snapdragon-powered Windows Copilot+ PCs (e.g. Snapdragon X Elite / X Plus with Hexagon NPU 45 TOPS) and validate selected AI workloads on actual target hardware while maintaining full development compatibility on non-Snapdragon host PCs.

## Current status

- Development host: Lenovo ThinkBook 14 G4 IAP (Intel Core i3-1215U, 8 GB RAM, Windows 11 Pro).
- Snapdragon support: Implemented as an isolated, pluggable provider layer (`backend/app/providers/qualcomm/`).
- Local zero-weight fallback ensures seamless development on 8 GB RAM without requiring Snapdragon hardware or downloading heavy neural weights.
- Actual hardware claims require target device execution.

## Deployment Architecture

```text
ScholarEdge Application (FastAPI + React)
        ↓
Provider Factory (`backend/app/providers/factory.py`)
        ↓
Qualcomm Provider Layer (`backend/app/providers/qualcomm/`)
  ├── QualcommEmbeddingProvider (all-MiniLM-L6-v2, 384-d)
  ├── QualcommLLMProvider (Qwen2.5-3B-Instruct / Llama-3.2-3B)
  └── QualcommVisionProvider (MobileNet-v2 / CLIP)
        ↓
ONNX Runtime with QNN Execution Provider (`QnnHtp.dll` on Hexagon NPU)
  └── Fallback: CPUExecutionProvider / Development fallback
        ↓
Target Hardware (Snapdragon X Elite / Copilot+ PC)
```

## Qualcomm AI Hub Verified Candidate Models

| Modality | Candidate Model | Target Precision | NPU Runtime Target |
|---|---|---|---|
| **Embeddings** | `all-MiniLM-L6-v2` | INT8 / FP16 | ONNX Runtime + QNN HTP |
| **Grounded LLM** | `Qwen2.5-3B-Instruct` / `Llama-3.2-3B` | INT4 (W4A16) | ONNX Runtime GenAI + QNN HTP |
| **Vision / Figures** | `MobileNet-v2` / `CLIP-ViT-B-32` | INT8 / FP16 | ONNX Runtime + QNN HTP |
| **OCR** | `EasyOCR` / `TrOCR` | INT8 | ONNX Runtime + QNN HTP |

## Target Environment Setup

To deploy on a physical Snapdragon Windows PC:

```powershell
# 1. Install ARM64 Python 3.11 or 3.12
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install ONNX Runtime with Qualcomm QNN Execution Provider
pip install onnxruntime-qnn

# 3. Configure Qualcomm Hexagon SDK runtime path
$env:PATH += ";C:\Program Files\Qualcomm\Hexagon_SDK\lib\hexagon_nn_skel"

# 4. Run ScholarEdge with Qualcomm backend
$env:PROVIDER_BACKEND = "qualcomm"
$env:QUALCOMM_DEVICE_TARGET = "Snapdragon X Elite"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Reproducible Benchmark Harness

Run the automated benchmark harness to collect all 9 required metrics:

```powershell
# From backend directory:
python scripts/benchmark_snapdragon.py --dry-run
```

The script automatically probes system telemetry, measures cold vs warm latency, token generation throughput, peak memory delta, and writes a reproducible JSON record to `backend/benchmarks/snapdragon_benchmark_<timestamp>.json`.

