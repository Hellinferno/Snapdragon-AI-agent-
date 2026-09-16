#!/usr/bin/env python3
"""
Compile and profile all-MiniLM-L6-v2 on Qualcomm AI Hub for Snapdragon X Elite.

Prerequisites:
1. Qualcomm account + AI Hub access
2. qai-hub installed and configured: qai-hub configure --api_token <YOUR_TOKEN>
3. Model files in backend/models/embeddings/all-MiniLM-L6-v2/

Usage:
    python scripts/compile_minilm_qai_hub.py --compile
    python scripts/compile_minilm_qai_hub.py --profile
    python scripts/compile_minilm_qai_hub.py --compile --profile
"""

import argparse
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import qai_hub as hub


MODEL_DIR = BACKEND_DIR / "models" / "embeddings" / "all-MiniLM-L6-v2"
MODEL_ONNX = MODEL_DIR / "model.onnx"
DEVICE = "Snapdragon X Elite CRD"
TARGET_RUNTIME = "onnx"


def submit_compile():
    """Submit compilation job to AI Hub."""
    print(f"Submitting compile job for {MODEL_ONNX}")
    print(f"Target device: {DEVICE}")
    print(f"Target runtime: {TARGET_RUNTIME}")

    client = hub.Client()

    compile_job = client.submit_compile_job(
        model=str(MODEL_ONNX),
        device=hub.Device(DEVICE),
        options=f"--target_runtime {TARGET_RUNTIME}",
    )

    print(f"Compile job submitted: {compile_job.job_id}")
    print(f"Status URL: https://aihub.qualcomm.com/jobs/{compile_job.job_id}")

    # Wait for completion
    compiled_model = compile_job.get_target_model()
    print(f"Compilation completed!")
    print(f"Compiled model: {compiled_model}")

    # Save compiled model locally
    output_path = MODEL_DIR / "model_snapdragon_x_elite.onnx"
    compiled_model.download(str(output_path))
    print(f"Compiled model saved to: {output_path}")

    return compiled_model


def submit_profile(compiled_model=None):
    """Submit profiling job to AI Hub."""
    if compiled_model is None:
        # Try to use previously compiled model
        output_path = MODEL_DIR / "model_snapdragon_x_elite.onnx"
        if not output_path.exists():
            print("No compiled model found. Run with --compile first.")
            return
        print(f"Using local compiled model: {output_path}")
        model_arg = str(output_path)
    else:
        model_arg = compiled_model

    print(f"Submitting profile job")
    print(f"Target device: {DEVICE}")
    print(f"Runtime: ONNX Runtime")
    print(f"Execution Provider: QNN")
    print(f"Compute Unit: NPU")

    client = hub.Client()

    profile_job = client.submit_profile_job(
        model=model_arg,
        device=hub.Device(DEVICE),
        options="--target_runtime onnx --onnx_execution_providers qnn --compute_unit npu",
    )

    print(f"Profile job submitted: {profile_job.job_id}")
    print(f"Status URL: https://aihub.qualcomm.com/jobs/{profile_job.job_id}")

    # Wait for completion
    profile = profile_job.get_profile()
    print(f"Profiling completed!")
    print(f"Profile: {profile}")

    # Print key metrics
    if hasattr(profile, 'data') and profile.data:
        print("\n=== PROFILE RESULTS ===")
        for key, value in profile.data.items():
            print(f"  {key}: {value}")

    return profile


def main():
    parser = argparse.ArgumentParser(description="Compile/profile MiniLM on Qualcomm AI Hub")
    parser.add_argument("--compile", action="store_true", help="Submit compile job")
    parser.add_argument("--profile", action="store_true", help="Submit profile job")
    args = parser.parse_args()

    if not args.compile and not args.profile:
        parser.print_help()
        return

    # Verify model exists
    if not MODEL_ONNX.exists():
        print(f"Model not found: {MODEL_ONNX}")
        print("Run: python scripts/download_embedding_model.py")
        return

    # Verify qai-hub is configured
    try:
        client = hub.Client()
        devices = client.get_devices()
        device_names = [d.name for d in devices]
        print(f"Available devices: {device_names}")
        if DEVICE not in device_names:
            print(f"WARNING: {DEVICE} not in device list. Available: {device_names}")
    except Exception as e:
        print(f"Error: qai-hub not configured or API token invalid: {e}")
        print("Run: qai-hub configure --api_token <YOUR_TOKEN>")
        return

    compiled_model = None
    if args.compile:
        compiled_model = submit_compile()

    if args.profile:
        submit_profile(compiled_model)


if __name__ == "__main__":
    main()