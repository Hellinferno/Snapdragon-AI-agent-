#!/usr/bin/env python3
"""Downloads the sentence-transformers all-MiniLM-L6-v2 ONNX export (Apache-2.0).

Pinned to a HuggingFace revision and verified by sha256, so every machine indexes with
byte-identical weights. Files land in backend/models/embeddings/all-MiniLM-L6-v2/
(gitignored). Run from backend/:  python scripts/download_embedding_model.py
"""

import hashlib
import ssl
import sys
import urllib.request
from pathlib import Path

REPO = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
FILES = {
    # remote path -> (local name, sha256)
    "onnx/model.onnx": ("model.onnx", "6fd5d72fe4589f189f8ebc006442dbb529bb7ce38f8082112682524616046452"),
    "tokenizer.json": ("tokenizer.json", "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037"),
}
TARGET = Path(__file__).resolve().parent.parent / "models" / "embeddings" / "all-MiniLM-L6-v2"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    # OS trust store rather than certifi, for networks that re-sign TLS
    context = ssl.create_default_context()
    for remote, (name, expected) in FILES.items():
        dest = TARGET / name
        if dest.exists() and sha256(dest) == expected:
            print(f"ok      {dest}")
            continue
        url = f"https://huggingface.co/{REPO}/resolve/{REVISION}/{remote}"
        tmp = dest.with_suffix(dest.suffix + ".part")
        print(f"fetch   {url}")
        with urllib.request.urlopen(url, context=context, timeout=120) as response, tmp.open("wb") as out:
            while block := response.read(1 << 20):
                out.write(block)
        actual = sha256(tmp)
        if actual != expected:
            tmp.unlink()
            print(f"sha256 mismatch for {name}: expected {expected}, got {actual}", file=sys.stderr)
            return 1
        tmp.replace(dest)
        print(f"saved   {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
