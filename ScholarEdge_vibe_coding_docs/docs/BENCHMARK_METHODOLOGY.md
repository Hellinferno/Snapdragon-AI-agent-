# ScholarEdge — Benchmark Methodology & Evidence Guide

## 1. Overview

ScholarEdge includes a standardized, reproducible benchmark harness (`backend/scripts/benchmark_snapdragon.py`) designed to validate on-device AI workloads on Snapdragon Windows PCs (Snapdragon X Elite / X Plus) and track latency, throughput, and memory.

## 2. Nine Benchmark Criteria

As mandated by `docs/SNAPDRAGON.md`, every benchmark execution records:

1. **Model / Version**: Identifier of the neural model (e.g. `all-MiniLM-L6-v2`, `Qwen3-4B-Instruct-2507`, `MobileNet-v2`).
2. **Runtime / Version**: Execution framework and exact version (e.g. `onnxruntime-qnn` for embedding/vision or GenAI Inference Extensions for the LLM, plus Python version).
3. **Target Snapdragon Device**: Device identification probed from platform telemetry (e.g. `Snapdragon X Elite Copilot+ PC`).
4. **Precision / Quantization**: Weights format (`INT4 (W4A16)`, `INT8`, `FP16`).
5. **Cold vs Warm Latency**: First-token / first-embedding invocation vs steady-state warm iteration mean and p95.
6. **Memory Footprint**: Peak memory delta during execution measured via memory tracing (`tracemalloc` / `psutil`).
7. **Accelerator Execution Verification**: Confirms `QNNExecutionProvider` for embedding/vision or a validated QAIRT runtime for the LLM; one does not prove the other.
8. **Application-Level Latency**: Full RAG pipeline latency (query embedding + vector search + prompt construction + grounded synthesis).
9. **Reproducible Configuration**: Timestamped JSON artifact saved to `backend/benchmarks/`.

## 3. Running Benchmarks

### On Development Machine (Simulation & Telemetry Verification)

```powershell
cd backend
.\.venv\Scripts\python scripts/benchmark_snapdragon.py --dry-run
```

### On Target Snapdragon Hardware

```powershell
cd backend
$env:PROVIDER_BACKEND = "qualcomm"
$env:QUALCOMM_DEVICE_TARGET = "Snapdragon X Elite"
python scripts/benchmark_snapdragon.py --output-dir ./benchmarks
```

## 4. Benchmark Output Schema

The generated JSON file has the following schema:

```json
{
  "timestamp_utc": "2026-09-08T08:21:58.123456Z",
  "harness_version": "1.0.0",
  "system_telemetry": {
    "os": "Windows 11 ...",
    "machine": "ARM64",
    "onnxruntime_version": "1.20.0",
    "qnn_execution_provider_active": true,
    "detected_device": "Snapdragon Copilot+ PC (ARM64)"
  },
  "configuration": {
    "device_target": "Snapdragon X Elite",
    "embedding_vision_provider": "QNNExecutionProvider",
    "llm_runtime": "GenAI Inference Extensions (QAIRT)",
    "precision": "int4",
    "embedding_model": "all-MiniLM-L6-v2",
    "llm_model": "Qwen3-4B-Instruct-2507"
  },
  "benchmarks": {
    "embedding": {
      "status": "record only after physical QNN validation"
    },
    "llm": {
      "status": "QAIRT inference and physical validation pending"
    },
    "application_e2e": {
      "status": "record only after all component runtimes are validated"
    }
  }
}
```
