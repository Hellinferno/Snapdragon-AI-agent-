#!/usr/bin/env python3
"""
Compile and profile all Qualcomm models on AI Hub for Snapdragon X Elite.

Models:
1. all-MiniLM-L6-v2 (embeddings)
2. Qwen2.5-3B-Instruct (LLM)
3. MobileNet-v2 (vision)

Prerequisites:
1. Qualcomm account + AI Hub access
2. qai-hub installed and configured: qai-hub configure --api_token <YOUR_TOKEN>
3. Models in backend/models/qualcomm/

Usage:
    python scripts/compile_qualcomm_models.py --compile
    python scripts/compile_qualcomm_models.py --profile
    python scripts/compile_qualcomm_models.py --compile --profile
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import qai_hub as hub


MODEL_DIR = BACKEND_DIR / "models" / "qualcomm"
DEVICE = "Snapdragon X Elite CRD"
TARGET_RUNTIME = "onnx"

MODELS = {
    "all-MiniLM-L6-v2": {
        "path": MODEL_DIR / "all-MiniLM-L6-v2" / "model.onnx",
        "compile_options": f"--target_runtime {TARGET_RUNTIME}",
        "profile_options": f"--target_runtime {TARGET_RUNTIME} --onnx_execution_providers qnn --compute_unit npu",
    },
    "Qwen2.5-3B-Instruct": {
        "path": MODEL_DIR / "Qwen2.5-3B-Instruct" / "model.onnx",
        "compile_options": f"--target_runtime {TARGET_RUNTIME}",
        "profile_options": f"--target_runtime {TARGET_RUNTIME} --onnx_execution_providers qnn --compute_unit npu",
    },
    "MobileNet-v2": {
        "path": MODEL_DIR / "MobileNet-v2" / "model.onnx",
        "compile_options": f"--target_runtime {TARGET_RUNTIME}",
        "profile_options": f"--target_runtime {TARGET_RUNTIME} --onnx_execution_providers qnn --compute_unit npu",
    },
}


def verify_models():
    """Check all model files exist."""
    missing = []
    for name, info in MODELS.items():
        if not info["path"].exists():
            missing.append(f"{name}: {info['path']}")
    if missing:
        print("Missing models:")
        for m in missing:
            print(f"  {m}")
        return False
    print("All model files found:")
    for name, info in MODELS.items():
        print(f"  {name}: {info['path']}")
    return True


def submit_compile(model_name: str):
    """Submit compilation job to AI Hub."""
    info = MODELS[model_name]
    model_path = info["path"]
    compile_options = info["compile_options"]

    print(f"\n{'='*60}")
    print(f"COMPILING: {model_name}")
    print(f"{'='*60}")
    print(f"Model: {model_path}")
    print(f"Device: {DEVICE}")
    print(f"Options: {compile_options}")

    client = hub.Client()

    compile_job = client.submit_compile_job(
        model=str(model_path),
        device=hub.Device(DEVICE),
        options=compile_options,
    )

    print(f"Compile job submitted: {compile_job.job_id}")
    print(f"Status URL: https://aihub.qualcomm.com/jobs/{compile_job.job_id}")

    # Wait for completion
    print("Waiting for compilation to complete...")
    compiled_model = compile_job.get_target_model()
    print(f"Compilation completed!")

    # Save compiled model locally
    output_path = info["path"].parent / f"{model_name}_snapdragon_x_elite.onnx"
    compiled_model.download(str(output_path))
    print(f"Compiled model saved to: {output_path}")

    return compiled_model


def submit_profile(model_name: str, compiled_model=None):
    """Submit profiling job to AI Hub."""
    info = MODELS[model_name]
    profile_options = info["profile_options"]

    print(f"\n{'='*60}")
    print(f"PROFILING: {model_name}")
    print(f"{'='*60}")
    print(f"Device: {DEVICE}")
    print(f"Options: {profile_options}")

    if compiled_model is None:
        # Try to use previously compiled model
        output_path = info["path"].parent / f"{model_name}_snapdragon_x_elite.onnx"
        if not output_path.exists():
            print(f"Compiled model not found: {output_path}")
            print("Run with --compile first.")
            return None
        print(f"Using local compiled model: {output_path}")
        model_arg = str(output_path)
    else:
        model_arg = compiled_model

    client = hub.Client()

    profile_job = client.submit_profile_job(
        model=model_arg,
        device=hub.Device(DEVICE),
        options=profile_options,
    )

    print(f"Profile job submitted: {profile_job.job_id}")
    print(f"Status URL: https://aihub.qualcomm.com/jobs/{profile_job.job_id}")

    # Wait for completion
    print("Waiting for profiling to complete...")
    profile = profile_job.get_profile()
    print(f"Profiling completed!")

    # Print key metrics
    if hasattr(profile, 'data') and profile.data:
        print(f"\n=== PROFILE RESULTS: {model_name} ===")
        for key, value in profile.data.items():
            print(f"  {key}: {value}")

    return profile


def main():
    parser = argparse.ArgumentParser(description="Compile/profile Qualcomm models on AI Hub")
    parser.add_argument("--compile", action="store_true", help="Submit compile jobs")
    parser.add_argument("--profile", action="store_true", help="Submit profile jobs")
    parser.add_argument("--model", choices=list(MODELS.keys()), help="Specific model (default: all)")
    args = parser.parse_args()

    if not args.compile and not args.profile:
        parser.print_help()
        return

    # Verify models exist
    if not verify_models():
        return

    # Verify qai-hub is configured
    try:
        client = hub.Client()
        devices = client.get_devices()
        device_names = [d.name for d in devices]
        print(f"Available devices: {device_names}")
        if DEVICE not in device_names:
            print(f"WARNING: {DEVICE} not in device list.")
    except Exception as e:
        print(f"Error: qai-hub not configured or API token invalid: {e}")
        print("Run: qai-hub configure --api_token <YOUR_TOKEN>")
        return

    models_to_process = [args.model] if args.model else list(MODELS.keys())

    compiled_models = {}
    if args.compile:
        for name in models_to_process:
            compiled_models[name] = submit_compile(name)

    if args.profile:
        for name in models_to_process:
            submit_profile(name, compiled_models.get(name))

    print("\n=== All jobs completed ===")
    print("Check https://aihub.qualcomm.com for detailed results.")


if __name__ == "__main__":
    main()