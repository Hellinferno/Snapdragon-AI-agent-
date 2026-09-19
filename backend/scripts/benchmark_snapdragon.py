"""ScholarEdge — Snapdragon & On-Device Benchmark Harness.

Implements all 9 reproducible criteria defined in docs/SNAPDRAGON.md:
1. record model/version
2. record runtime/version
3. record target Snapdragon device
4. record precision/quantization
5. record warm/cold latency
6. record memory
7. record accelerator execution
8. record application-level latency
9. store reproducible benchmark configuration
"""

import sys
import os
import time
import json
import platform
import argparse
import asyncio
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

# Ensure backend package is in python path
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.providers.qualcomm.qualcomm_config import QualcommConfig, QualcommModelUnavailable
from app.providers.qualcomm.qualcomm_providers import (
    QualcommEmbeddingProvider,
    QualcommLLMProvider,
    QualcommVisionProvider,
)


def detect_system_telemetry() -> Dict[str, Any]:
    """Detect host platform, architecture, and accelerator capabilities."""
    uname = platform.uname()
    is_arm64 = uname.machine.lower() in ("arm64", "aarch64")
    is_windows = uname.system.lower() == "windows"

    ort_version = "not_installed"
    available_providers = []
    try:
        import onnxruntime as ort
        ort_version = ort.__version__
        available_providers = ort.get_available_providers()
    except ImportError:
        pass

    qnn_active = "QNNExecutionProvider" in available_providers
    detected_device = "Snapdragon Copilot+ PC (ARM64)" if (is_arm64 and is_windows) else f"{uname.system} {uname.machine}"

    return {
        "os": f"{uname.system} {uname.release} (Build {uname.version})",
        "machine": uname.machine,
        "processor": uname.processor,
        "python_version": platform.python_version(),
        "onnxruntime_version": ort_version,
        "available_providers": available_providers,
        "qnn_execution_provider_active": qnn_active,
        "detected_device": detected_device,
        "is_target_snapdragon": is_arm64 and is_windows,
    }


def run_embedding_benchmark(
    provider: QualcommEmbeddingProvider,
    iterations: int = 5,
) -> Dict[str, Any]:
    """Benchmark embedding generation cold vs warm latency and memory."""
    tracemalloc.start()
    t_start_mem = tracemalloc.get_traced_memory()[0]

    sample_query = "Quantized transformer inference on Hexagon NPU with 4-bit weights"
    sample_corpus = [
        f"Sample passage #{i} discussing on-device acceleration and low latency neural computation."
        for i in range(10)
    ]

    # Cold run
    t0 = time.perf_counter()
    _ = asyncio.run(provider.embed_text(sample_query))
    cold_latency_ms = (time.perf_counter() - t0) * 1000.0

    # Warm runs
    warm_latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        asyncio.run(provider.embed_batch(sample_corpus))
        warm_latencies.append((time.perf_counter() - t0) * 1000.0)

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    avg_warm_ms = sum(warm_latencies) / len(warm_latencies) if warm_latencies else 0.0

    return {
        "model_id": provider.config.embedding_model_id,
        "precision": provider.config.precision,
        "cold_latency_ms": round(cold_latency_ms, 2),
        "warm_mean_latency_ms": round(avg_warm_ms, 2),
        "warm_p95_latency_ms": round(sorted(warm_latencies)[int(len(warm_latencies) * 0.95)], 2),
        "batch_size": len(sample_corpus),
        "peak_memory_delta_mb": round((peak_mem - t_start_mem) / (1024 * 1024), 3),
        "accelerator_execution": provider.telemetry.get("accelerator_active", False),
    }


def run_llm_benchmark(
    provider: QualcommLLMProvider,
    iterations: int = 3,
) -> Dict[str, Any]:
    """Benchmark grounded LLM generation latency, tokens/sec, and memory."""
    tracemalloc.start()
    t_start_mem = tracemalloc.get_traced_memory()[0]

    prompt = (
        "### CONTEXT:\n"
        "[Source 1: Snapdragon Architecture Paper, Page 3, Section: NPU Core]\n"
        "The Hexagon NPU delivers up to 45 TOPS of INT4 compute while maintaining thermal efficiency on thin-and-light laptop designs.\n\n"
        "[Source 2: Snapdragon Architecture Paper, Page 5, Section: Memory System]\n"
        "Memory bandwidth constraints are mitigated through dedicated tightly coupled system cache and hardware-directed weight decompression.\n"
        "### QUESTION:\n"
        "What is the compute throughput of the Hexagon NPU and how are bandwidth constraints addressed?"
    )

    # Cold run
    t0 = time.perf_counter()
    cold_res = asyncio.run(provider.generate(prompt))
    cold_latency_ms = (time.perf_counter() - t0) * 1000.0

    # Warm runs
    warm_latencies = []
    tokens_per_sec_list = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        res = asyncio.run(provider.generate(prompt))
        elapsed = (time.perf_counter() - t0) * 1000.0
        warm_latencies.append(elapsed)
        word_count = len(res.text.split())
        tps = (word_count * 1.3) / max(0.001, (elapsed / 1000.0))
        tokens_per_sec_list.append(tps)

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    avg_warm_ms = sum(warm_latencies) / len(warm_latencies) if warm_latencies else 0.0
    avg_tps = sum(tokens_per_sec_list) / len(tokens_per_sec_list) if tokens_per_sec_list else 0.0

    return {
        "model_id": provider.config.llm_model_id,
        "precision": provider.config.precision,
        "cold_latency_ms": round(cold_latency_ms, 2),
        "warm_mean_latency_ms": round(avg_warm_ms, 2),
        "tokens_per_second": round(avg_tps, 1),
        "peak_memory_delta_mb": round((peak_mem - t_start_mem) / (1024 * 1024), 3),
        "completion_tokens": cold_res.completion_tokens,
        "accelerator_execution": provider.telemetry.get("accelerator_active", False),
    }


def run_full_benchmark(output_dir: Path, dry_run: bool = False) -> Path:
    """Execute complete benchmark suite and persist reproducible artifact."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"snapdragon_benchmark_{timestamp}.json"

    print("=" * 70)
    print(" ScholarEdge — Snapdragon & On-Device Benchmark Harness")
    print("=" * 70)

    system_info = detect_system_telemetry()
    print(f"Target Device:        {system_info['detected_device']}")
    print(f"Operating System:     {system_info['os']}")
    print(f"Architecture:         {system_info['machine']} ({system_info['processor']})")
    print(f"ONNX Runtime:         {system_info['onnxruntime_version']}")
    print(f"Available Providers:  {', '.join(system_info['available_providers']) or 'None'}")
    print(f"QNN NPU Active:       {'YES' if system_info['qnn_execution_provider_active'] else 'NO (CPU Fallback)'}")
    mode_label = "QUALCOMM PHYSICAL NPU" if (system_info['is_target_snapdragon'] and system_info['qnn_execution_provider_active']) else "DEVELOPMENT HOST SIMULATION (Baseline)"
    print(f"Benchmark Mode:       {mode_label}")
    print(f"Target Checklist:     {'VERIFIED' if (system_info['is_target_snapdragon'] and system_info['qnn_execution_provider_active']) else 'PENDING TARGET-DEVICE VALIDATION'}")
    print("-" * 70)

    config = QualcommConfig()
    
    # Embedding provider may fail due to ONNX IR version mismatch
    try:
        embedding_prov = QualcommEmbeddingProvider(config)
    except RuntimeError as e:
        if "Unsupported model IR version" in str(e):
            print("Embedding provider unavailable (ONNX IR version mismatch), skipping embedding benchmark")
            embedding_prov = None
        else:
            raise
    else:
        # Check if session was initialized successfully
        if embedding_prov is not None and embedding_prov._session is None:
            print("Embedding provider unavailable (ONNX IR version mismatch), skipping embedding benchmark")
            embedding_prov = None
    
    llm_prov = QualcommLLMProvider(config)
    
    # Vision provider needs its own ONNX artifact, which is absent on a fresh
    # clone and on CI (backend/models/ is gitignored).
    try:
        vision_prov = QualcommVisionProvider(config)
    except QualcommModelUnavailable as e:
        print(f"      Vision provider unavailable: {e}")
        vision_prov = None
    except RuntimeError as e:
        if "Unsupported model IR version" in str(e):
            print("Vision provider unavailable (ONNX IR version mismatch), skipping vision benchmark")
            vision_prov = None
        else:
            raise

    print("\n[1/3] Benchmarking Qualcomm Embedding Pipeline (all-MiniLM-L6-v2)...")
    if embedding_prov is None:
        print("      Skipped (ONNX IR version mismatch)")
        emb_results = {"cold_latency_ms": 0, "warm_mean_latency_ms": 0, "peak_memory_delta_mb": 0}
    else:
        emb_results = run_embedding_benchmark(embedding_prov, iterations=3 if dry_run else 5)
        print(f"      Cold Latency:       {emb_results['cold_latency_ms']:.2f} ms")
        print(f"      Warm Mean Latency:  {emb_results['warm_mean_latency_ms']:.2f} ms (10-chunk batch)")
        print(f"      Peak Memory Delta:  {emb_results['peak_memory_delta_mb']:.3f} MB")

    print("\n[2/3] Benchmarking Qualcomm Grounded LLM Pipeline (Qwen3-4B-Instruct-2507)...")
    if getattr(llm_prov, "_qairt_bundle_detected", False):
        # Honest state: the QAIRT model bundle exists on disk, but QAIRT/GenieX
        # inference is unavailable on this host (no Snapdragon NPU / SDK).
        print(
            "      Skipped (QAIRT bundle detected, but QAIRT/GenAI Inference Extensions "
            "runtime is unavailable on this host - requires Snapdragon NPU + SDK)"
        )
        llm_results = {
            "cold_latency_ms": 0,
            "warm_mean_latency_ms": 0,
            "tokens_per_second": 0,
            "peak_memory_delta_mb": 0,
            "status": "QAIRT_BUNDLE_DETECTED_RUNTIME_UNAVAILABLE",
        }
    elif llm_prov._session is None or llm_prov._tokenizer is None:
        print("      Skipped (QAIRT bundle not found on this host)")
        llm_results = {
            "cold_latency_ms": 0,
            "warm_mean_latency_ms": 0,
            "tokens_per_second": 0,
            "peak_memory_delta_mb": 0,
            "status": "QAIRT_BUNDLE_NOT_FOUND",
        }
    else:
        llm_results = run_llm_benchmark(llm_prov, iterations=2 if dry_run else 3)
        print(f"      Cold Latency:       {llm_results['cold_latency_ms']:.2f} ms")
        print(f"      Warm Mean Latency:  {llm_results['warm_mean_latency_ms']:.2f} ms")
        print(f"      Throughput:         ~{llm_results['tokens_per_second']:.1f} tokens/sec")
        print(f"      Peak Memory Delta:  {llm_results['peak_memory_delta_mb']:.3f} MB")

    print("\n[3/3] Benchmarking Application-Level Grounded Retrieval Latency...")
    if embedding_prov is not None and (llm_prov._session is not None and llm_prov._tokenizer is not None):
        app_cold_ms = emb_results["cold_latency_ms"] + llm_results["cold_latency_ms"]
        app_warm_ms = (emb_results["warm_mean_latency_ms"] / 10.0) + llm_results["warm_mean_latency_ms"]
        print(f"      Cold End-to-End:    {app_cold_ms:.2f} ms")
        print(f"      Warm End-to-End:    {app_warm_ms:.2f} ms")
    else:
        print("      Skipped (components unavailable)")
        app_cold_ms = 0
        app_warm_ms = 0

    # Determine execution mode and target device checklist status
    is_target_snapdragon = system_info.get("is_target_snapdragon", False)
    qnn_active = system_info.get("qnn_execution_provider_active", False)
    models_present = (config.model_dir / "all-MiniLM-L6-v2" / "model.onnx").exists()

    if is_target_snapdragon and qnn_active and models_present:
        benchmark_mode = "QUALCOMM_QNN_NPU_VERIFIED"
        hardware_npu_verified = True
        notes = "Empirical verification on physical Snapdragon Windows Copilot+ PC with Hexagon NPU QNN execution."
    else:
        benchmark_mode = "DEVELOPMENT_HOST_SIMULATION"
        hardware_npu_verified = False
        notes = (
            "Execution ran in development fallback / host simulation mode on non-Snapdragon host "
            f"({system_info.get('machine')}). Measurements reflect host CPU baseline and must NOT "
            "be cited as physical Qualcomm Hexagon NPU performance. Physical NPU numbers require "
            "completing the target device checklist on an ARM64 Windows Copilot+ PC."
        )

    checklist = {
        "arm64_windows_host": is_target_snapdragon,
        "onnxruntime_qnn_installed": qnn_active,
        "qnn_execution_provider_active": qnn_active,
        "model_artifacts_present": models_present,
        "validation_status": "VERIFIED" if hardware_npu_verified else "PENDING_TARGET_DEVICE_VALIDATION",
    }

    benchmark_record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "harness_version": "1.1.0",
        "benchmark_mode": benchmark_mode,
        "hardware_npu_verified": hardware_npu_verified,
        "notes": notes,
        "target_device_checklist": checklist,
        "system_telemetry": system_info,
        "configuration": {
            "device_target": config.device_target,
            "preferred_provider": config.preferred_provider,
            "fallback_provider": config.fallback_provider,
            "qnn_backend_path": config.qnn_backend_path,
            "precision": config.precision,
            "embedding_model": config.embedding_model_id,
            "llm_model": config.llm_model_id,
            "vision_model": config.vision_model_id,
        },
        "benchmarks": {
            "embedding": emb_results,
            "llm": llm_results,
            "application_e2e": {
                "cold_e2e_latency_ms": round(app_cold_ms, 2),
                "warm_e2e_latency_ms": round(app_warm_ms, 2),
                "total_peak_memory_delta_mb": round(
                    emb_results["peak_memory_delta_mb"] + llm_results["peak_memory_delta_mb"], 3
                ),
            },
        },
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_record, f, indent=2)

    print("\n" + "=" * 70)
    print(f" Benchmark results written to:\n {output_file.resolve()}")
    print("=" * 70)

    return output_file


def main():
    parser = argparse.ArgumentParser(description="ScholarEdge Snapdragon & On-Device Benchmark Harness")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=backend_root / "benchmarks",
        help="Directory to save benchmark JSON artifacts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run a quick verification pass without extensive iterations",
    )
    args = parser.parse_args()
    run_full_benchmark(args.output_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
