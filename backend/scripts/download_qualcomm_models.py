#!/usr/bin/env python3
"""Download Qwen2.5-3B-Instruct ONNX and MobileNet-v2 ONNX models for Qualcomm AI Hub.

Places models in models/qualcomm/ structure expected by the providers.
"""

import hashlib
import ssl
import sys
import urllib.request
from pathlib import Path

# Models to download
# Format: repo -> (revision, files_to_download)
# files: remote_path -> (local_name, expected_sha256_or_none)

MODELS = {
    "Qwen2.5-3B-Instruct": {
        "repo": "Qwen/Qwen2.5-3B-Instruct",
        "revision": "master",
        "files": {
            # Note: Qwen ONNX exports may not be directly on HF. 
            # We may need to export from PyTorch or use Qualcomm AI Hub precompiled models.
            "onnx/model.onnx": ("model.onnx", None),  # Will need to export if not available
        }
    },
    "MobileNet-v2": {
        "repo": "onnx/models",
        "revision": "main",
        "files": {
            "vision/classification/mobilenet/model/mobilenetv2-1.0.onnx": ("model.onnx", None),
        }
    }
}

TARGET_BASE = Path(__file__).resolve().parent.parent / "models" / "qualcomm"


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


def download_model(model_name: str, info: dict):
    repo = info["repo"]
    revision = info["revision"]
    files = info["files"]
    
    model_dir = TARGET_BASE / model_name
    model_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n=== {model_name} ===")
    print(f"Target: {model_dir}")
    
    all_ok = True
    for remote_path, (local_name, expected_sha256) in files.items():
        dest = model_dir / local_name
        if dest.exists():
            if expected_sha256 and sha256(dest) != expected_sha256:
                print(f"  Re-downloading {local_name} (sha256 mismatch)")
            else:
                print(f"  Already exists: {dest}")
                continue
        
        url = f"https://huggingface.co/{repo}/resolve/{revision}/{remote_path}"
        if not download_file(url, dest, expected_sha256):
            all_ok = False
    
    return all_ok


def main():
    TARGET_BASE.mkdir(parents=True, exist_ok=True)
    
    print("Downloading models for Qualcomm AI Hub...")
    print(f"Base directory: {TARGET_BASE}")
    
    # First, copy existing MiniLM to qualcomm structure
    minilm_src = Path(__file__).resolve().parent.parent / "models" / "embeddings" / "all-MiniLM-L6-v2"
    minilm_dst = TARGET_BASE / "all-MiniLM-L6-v2"
    if minilm_src.exists() and not minilm_dst.exists():
        import shutil
        shutil.copytree(minilm_src, minilm_dst)
        print(f"Copied MiniLM to: {minilm_dst}")
    elif minilm_dst.exists():
        print(f"MiniLM already at: {minilm_dst}")
    
    # Download other models
    results = {}
    for name, info in MODELS.items():
        results[name] = download_model(name, info)
    
    print("\n=== Summary ===")
    for name, ok in results.items():
        status = "OK" if ok else "FAILED"
        print(f"  {name}: {status}")
    
    print(f"\nModels available at: {TARGET_BASE}")
    for p in TARGET_BASE.iterdir():
        if p.is_dir():
            onnx = p / "model.onnx"
            print(f"  {p.name}: {'model.onnx' if onnx.exists() else 'MISSING'}")


if __name__ == "__main__":
    main()