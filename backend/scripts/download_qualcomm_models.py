#!/usr/bin/env python3
"""Download and verify Qualcomm AI Hub model artifacts.

Places verified ONNX models for the embedding and vision providers in the
models/qualcomm/ structure expected by the providers.

This script:
1. Verifies existing model.onnx files are real (not fake generated)
2. Uses AI Hub compiled ONNX models when available (model_snapdragon_x_elite.onnx)
3. Downloads real models from proper sources
4. Does NOT generate fake models with random weights
"""

import hashlib
import ssl
import sys
import urllib.request
from pathlib import Path

# Model definitions with SHA256 for verification
# These are the real models we expect
MODELS = {
    "MobileNet-v2": {
        "repo": "onnx/models",
        "revision": "main",
        "files": {
            "vision/classification/mobilenet/model/mobilenetv2-1.0.onnx": ("model.onnx", None),
        },
        "ai_hub_compiled": True,
        "compiled_name": "model_snapdragon_x_elite.onnx",
    },
    "all-MiniLM-L6-v2": {
        "repo": "sentence-transformers/all-MiniLM-L6-v2",
        "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        "files": {
            "onnx/model.onnx": ("model.onnx", "6fd5d72fe4589f189f8ebc006442dbb529bb7ce38f8082112682524616046452"),
            "tokenizer.json": ("tokenizer.json", "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037"),
        },
        "ai_hub_compiled": True,
        "compiled_name": "model_snapdragon_x_elite.onnx",
    },
}

TARGET_BASE = Path(__file__).resolve().parent.parent / "models" / "qualcomm"

# Known fake model signatures (from setup_qualcomm_onnx_models.py)
# These are the fake models generated with random weights
FAKE_MODEL_SIGNATURES = {
    "MobileNet-v2": {
        "size_approx": 2_400_000,  # ~2.4 MB
        "classes": 4,
    },
    "all-MiniLM-L6-v2": {
        "size_approx": 46_000_000,  # ~46 MB (the fake one is smaller than real)
        "vocab_size": 30522,
        "dim": 384,
    },
}

# Real model expected sizes (approximate)
REAL_MODEL_SIZES = {
    "MobileNet-v2": 2_400_000,  # ~2.4 MB for INT4 compiled
    "all-MiniLM-L6-v2": 46_000_000,  # ~46 MB for INT4 compiled
}


TARGET_BASE = Path(__file__).resolve().parent.parent / "models" / "qualcomm"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def is_fake_model(model_path: Path, model_name: str) -> bool:
    """Check if a model file is a fake generated model."""
    if not model_path.exists():
        return False
    
    try:
        import onnx
        model = onnx.load(str(model_path))
        
        # Check for fake model signatures
        fake_sig = FAKE_MODEL_SIGNATURES.get(model_name, {})
        
        # Check graph name
        if model.graph.name in ["all-MiniLM-L6-v2-qualcomm", "MobileNet-v2-qualcomm-vision"]:
            return True
        
        # Check producer name
        if "Qualcomm-AI-Hub-Exporter" in model.producer_name:
            return True
            
        # Check for fake MiniLM
        if model_name == "all-MiniLM-L6-v2":
            for init in model.graph.initializer:
                if init.name == "word_embeddings" and init.dims == [30522, 384]:
                    # Could be real or fake, need more checks
                    pass
                    
        # Check for fake MobileNet
        if model_name == "MobileNet-v2":
            for node in model.graph.node:
                if node.op_type == "Gemm" and "fc_weights" in node.input:
                    # Check if it's just a simple Gemm without proper MobileNet layers
                    return True
                    
    except Exception:
        pass
    
    return False


def verify_model(model_path: Path, model_name: str) -> tuple[bool, str]:
    """Verify a model is real and return (is_valid, message)."""
    if not model_path.exists():
        return False, "Model file does not exist"
    
    if is_fake_model(model_path, model_name):
        return False, f"Model appears to be fake/generated (not a real pretrained model)"
    
    # Check size is reasonable
    size = model_path.stat().st_size
    expected_size = REAL_MODEL_SIZES.get(model_name, 0)
    if expected_size > 0:
        if abs(size - expected_size) / expected_size > 0.5:
            return False, f"Model size {size} bytes unexpected (expected ~{expected_size})"
    
    # Try to load with ONNX Runtime
    try:
        import onnxruntime as ort
        session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        return True, "Model verified successfully"
    except Exception as e:
        return False, f"ONNX Runtime validation failed: {e}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download_file(url: str, dest: Path, expected_sha256: str | None = None) -> bool:
    context = ssl.create_default_context()
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        print(f"  Downloading: {url}")
        with urllib.request.urlopen(url, context=context, timeout=300) as response, tmp.open("wb") as out:
            while block := response.read(1 << 20):
                out.write(block)
        if expected_sha256:
            actual = sha256(tmp)
            if actual != expected_sha256:
                tmp.unlink()
                print(f"  SHA256 mismatch: expected {expected_sha256}, got {actual}")
                return False
        tmp.replace(dest)
        print(f"  Saved: {dest}")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        if tmp.exists():
            tmp.unlink()
        return False


def ensure_model(model_name: str, info: dict) -> bool:
    """Ensure a model is available and verified."""
    model_dir = TARGET_BASE / model_name
    model_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = model_dir / "model.onnx"
    compiled_path = model_dir / info.get("compiled_name", "model_snapdragon_x_elite.onnx")
    
    print(f"\n=== {model_name} ===")
    print(f"Target: {model_dir}")
    
    # First, check if model.onnx exists and is valid
    if model_path.exists():
        is_valid, msg = verify_model(model_path, model_name)
        if is_valid:
            print(f"  [OK] Using existing verified model: {model_path}")
            return True
        else:
            print(f"  [FAIL] Existing model invalid: {msg}")
            # Try compiled version
            if compiled_path.exists():
                is_valid, msg = verify_model(compiled_path, model_name)
                if is_valid:
                    print(f"  ✓ Using compiled AI Hub model: {compiled_path}")
                    # Replace model.onnx with compiled version
                    import shutil
                    shutil.copy2(compiled_path, model_path)
                    print(f"  ✓ Copied compiled model to model.onnx")
                    return True
                else:
                    print(f"  ✗ Compiled model also invalid: {msg}")
            # Remove invalid model
            print(f"  Removing invalid model...")
            model_path.unlink()
    
    # Try to use compiled AI Hub model if available
    if compiled_path.exists():
        is_valid, msg = verify_model(compiled_path, model_name)
        if is_valid:
            print(f"  ✓ Using AI Hub compiled model: {compiled_path}")
            import shutil
            shutil.copy2(compiled_path, model_path)
            print(f"  ✓ Copied compiled model to model.onnx")
            return True
        else:
            print(f"  ✗ Compiled model invalid: {msg}")
    
    # Try to download from proper source
    repo = model_info.get("repo")
    revision = model_info.get("revision")
    files = model_info.get("files", {})
    
    if not files:
        print(f"  No download source defined for {model_name}")
        return False
    
    print(f"  Attempting to download from Hugging Face...")
    for remote_path, (local_name, expected_sha256) in files.items():
        dest = model_dir / local_name
        url = f"https://huggingface.co/{repo}/resolve/{revision}/{remote_path}"
        
        # Try to download
        try:
            context = ssl.create_default_context()
            tmp = dest.with_suffix(dest.suffix + ".part")
            print(f"  Downloading: {url}")
            with urllib.request.urlopen(url, context=ssl.create_default_context(), timeout=300) as response, open(tmp, "wb") as out:
                while block := response.read(1 << 20):
                    out.write(block)
            if expected_sha256:
                actual = sha256(tmp)
                if actual != expected_sha256:
                    tmp.unlink()
                    print(f"  SHA256 mismatch: expected {expected_sha256}, got {actual}")
                    continue
            tmp.replace(dest)
            print(f"  Saved: {dest}")
            
            # Verify downloaded model
            if local_name == "model.onnx":
                is_valid, msg = verify_model(dest, model_name)
                if is_valid:
                    print(f"  ✓ Downloaded and verified: {dest}")
                    return True
                else:
                    print(f"  ✗ Downloaded model invalid: {msg}")
                    dest.unlink()
        
        except Exception as e:
            print(f"  ERROR downloading: {e}")
    
    return False


def main():
    TARGET_BASE.mkdir(parents=True, exist_ok=True)
    
    print("Verifying and acquiring Qualcomm ONNX models for embeddings and vision...")
    print(f"Base directory: {TARGET_BASE}")
    
    # First, handle MiniLM - copy from embeddings if needed
    minilm_src = Path(__file__).resolve().parent.parent / "models" / "embeddings" / "all-MiniLM-L6-v2"
    minilm_dst = TARGET_BASE / "all-MiniLM-L6-v2"
    
    if minilm_src.exists():
        model_path = minilm_dst / "model.onnx"
        if not model_path.exists():
            import shutil
            shutil.copytree(minilm_src, minilm_dst)
            print(f"Copied MiniLM from embeddings to: {minilm_dst}")
        else:
            print(f"MiniLM already at: {minilm_dst}")
    
    # Process each model
    results = {}
    for model_name, info in MODELS.items():
        if model_name == "all-MiniLM-L6-v2":
            # Already handled above
            model_path = TARGET_BASE / "all-MiniLM-L6-v2" / "model.onnx"
            is_valid, msg = verify_model(model_path, model_name)
            results[model_name] = is_valid
            print(f"  MiniLM: {'OK' if is_valid else 'FAILED'} - {msg}")
            continue
            
        results[model_name] = ensure_model(model_name, info)
    
    print("\n=== Summary ===")
    all_ok = True
    for name, ok in results.items():
        status = "OK" if ok else "FAILED"
        if not ok:
            all_ok = False
        print(f"  {name}: {status}")
    
    print(f"\nModels available at: {TARGET_BASE}")
    for p in TARGET_BASE.iterdir():
        if p.is_dir():
            onnx = p / "model.onnx"
            status = "OK" if onnx.exists() else "MISSING"
            print(f"  {p.name}: {status}")
    
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
