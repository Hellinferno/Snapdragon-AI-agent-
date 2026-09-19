"""Documentation consistency guard.

Markdown documentation in this repository repeatedly quotes machine-checkable
facts, and all three kinds drifted badly before this module existed:

1. **The size of the hermetic test suite.** Four documents simultaneously
   advertised 95, 79, 37 and 31 tests while the suite actually collected 115.
2. **Paths of evaluation result files.** ``DEMO.md`` cited a result file that was
   never committed, so a fresh clone could not reproduce the numbers it printed.
3. **The ``/api/health`` payload.** ``ARCHITECTURE.md`` documented four fields the
   endpoint never returns, plus a ``"verified"`` key it calls ``status``.

Everything here is deliberately narrow and objective: a doc either names the
current hermetic test count, or it does not. There are no fuzzy heuristics.

Conventions these checks enforce
-------------------------------
* A test count claim is written ``<N> hermetic tests`` (or the equivalent
  ``<N> tests``/``<N> passed``/``<N> passing``). ``N`` is the number of tests the
  default ``pytest`` run collects, i.e. everything except the opt-in
  ``integration``/``external_api``/``live`` modules. Do **not** quote the
  ``N passed`` figure from a summary line: it varies with which local ONNX
  models are present, whereas the collected count does not.
* Counts of *live*/*integration* tests are exempt, because those are stated as
  opt-in extras rather than as the size of the hermetic suite.
* Every ``*.json`` path named in the docs must exist **and be tracked by git**
  when it lives under ``evaluation/results/``; an untracked result file is not
  evidence a reader can obtain.
* Bare filenames (``baseline.json``) are resolved against
  ``backend/evaluation/results/``. Generic config names that are not result
  files are listed in :data:`EXEMPT_BARE_JSON`.
* Any ``json`` fenced block containing ``"hardware_npu_active"`` documents the
  runtime telemetry contract, and every field name in it (including inside
  ``privacy_checklist``) must be one the endpoint actually emits.

Usage::

    python -m scripts.check_docs          # from backend/, exits non-zero on drift

``tests/test_doc_consistency.py`` calls :func:`run_all_checks`, so this runs as
part of the normal suite instead of being a script someone must remember.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
RESULTS_ROOT = BACKEND_ROOT / "evaluation" / "results"

# Directories that hold third-party or generated content rather than our docs.
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    "htmlcov",
}

# Bare ``*.json`` names that are configuration, not evaluation evidence.
EXEMPT_BARE_JSON = frozenset(
    {
        "package.json",
        "package-lock.json",
        "tsconfig.json",
        "config.json",
        "settings.json",
    }
)

# ``115 hermetic tests`` / ``115 tests passing`` / ``pytest-115%20passed`` (badge
# URLs). The lookbehind excludes word characters and path separators, so version
# numbers and ``115/117`` collection lines are not mistaken for count claims, but
# a hyphen is allowed because the shield badge format is ``pytest-<N>%20passed``.
COUNT_CLAIM_RE = re.compile(
    r"(?<![\w./])(\d{1,4})(?:%20|[\s_-])+"
    r"(?:(?:automated|offline|hermetic|backend|integration|live|opt-?in|excluded|deselected)(?:%20|\s)+)*"
    r"(?:tests?|test\s+cases?|passed|passing)\b",
    re.IGNORECASE,
)

# Claims about the opt-in live suite are not claims about the hermetic suite.
NON_HERMETIC_QUALIFIERS = ("integration", "live", "opt-in", "optin", "external")

JSON_REF_RE = re.compile(r"[A-Za-z0-9_./~-]+\.json")

COLLECTION_LINE_RE = re.compile(r"^(\d+)/(\d+) tests collected", re.MULTILINE)


def iter_docs() -> list[Path]:
    """Return the tracked documentation set, newest discovery order irrelevant."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "*.md", "*.example"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        paths = [REPO_ROOT / line for line in out.splitlines() if line.strip()]
        if paths:
            return sorted(paths)
    except (OSError, subprocess.CalledProcessError):
        pass

    # Fallback for environments without git (e.g. an exported tarball).
    docs: list[Path] = []
    for path in REPO_ROOT.rglob("*.md"):
        if SKIP_DIRS & set(path.parts):
            continue
        docs.append(path)
    return sorted(docs)


@lru_cache(maxsize=1)
def hermetic_test_count() -> int:
    """Number of tests the default ``pytest`` run collects.

    Raises:
        RuntimeError: if pytest cannot collect, or reports errors. A broken
            collection is a real failure that must not be masked as a doc drift.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "--no-header"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = f"{proc.stdout}\n{proc.stderr}"
    match = COLLECTION_LINE_RE.search(output)
    if match is None:
        raise RuntimeError(
            "could not determine the collected test count; pytest said:\n"
            f"{output.strip()[-2000:]}"
        )
    return int(match.group(1))


def check_test_counts() -> list[str]:
    """Every hermetic count claim in the docs must equal the real count."""
    expected = hermetic_test_count()
    problems: list[str] = []
    for doc in iter_docs():
        text = doc.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in COUNT_CLAIM_RE.finditer(line):
                claim = match.group(0)
                if any(q in claim for q in NON_HERMETIC_QUALIFIERS):
                    continue
                value = int(match.group(1))
                if value != expected:
                    problems.append(
                        f"{doc.relative_to(REPO_ROOT)}:{line_no}: claims {value} "
                        f"({claim.strip()!r}) but the hermetic suite collects "
                        f"{expected}; write {expected} (live/integration counts "
                        f"are exempt)"
                    )
    return problems


@lru_cache(maxsize=1)
def _tracked_files() -> frozenset[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return frozenset()
    return frozenset(line.strip() for line in out.splitlines() if line.strip())


@lru_cache(maxsize=1)
def _result_json_basenames() -> frozenset[str]:
    if not RESULTS_ROOT.is_dir():
        return frozenset()
    return frozenset(p.name for p in RESULTS_ROOT.rglob("*.json"))


@lru_cache(maxsize=1)
def _health_payload_keys() -> tuple[frozenset[str], frozenset[str]] | None:
    """Top-level and privacy-checklist keys the real endpoint emits.

    Returns ``None`` when the endpoint cannot be imported/executed in this
    environment, in which case the check reports the failure instead of raising.
    """
    from app.api.health import _get_system_runtime_telemetry

    payload = _get_system_runtime_telemetry()
    rows = [r for r in (payload.get("privacy_checklist") or []) if isinstance(r, dict)]
    item_keys = frozenset().union(*(frozenset(r) for r in rows)) if rows else frozenset()
    return frozenset(payload), item_keys


def _fenced_json_blocks(text: str):
    """Yield ``(first_line_number, parsed_or_None, raw)`` for each ```json block."""
    for match in re.finditer(r"^```json\s*\n(.*?)^```", text, re.DOTALL | re.MULTILINE):
        first_line = text.count("\n", 0, match.start(1)) + 1
        raw = match.group(1)
        try:
            yield first_line, json.loads(raw), raw
        except json.JSONDecodeError:
            yield first_line, None, raw


def check_health_contract() -> list[str]:
    """Documented ``/api/health`` payloads must use fields the endpoint really returns.

    The architecture doc previously showed ``execution_provider``, ``host_device``,
    ``host_architecture`` and ``privacy_mode`` (none of which exist) and a
    ``"verified"`` key that the endpoint calls ``status`` — a reader would have
    coded against a payload that never existed. Snapdragon-mode examples are
    checked too: plausible-but-invented field names are how that drifted.
    """
    try:
        payload = _health_payload_keys()
    except Exception as exc:  # pragma: no cover - environment problem, reported not raised
        return [f"could not introspect the /api/health payload: {exc!r}"]
    top_level, item_keys = payload

    problems: list[str] = []
    for doc in iter_docs():
        text = doc.read_text(encoding="utf-8", errors="replace")
        for first_line, parsed, raw in _fenced_json_blocks(text):
            if "hardware_npu_active" not in raw or not isinstance(parsed, dict):
                continue
            rel = doc.relative_to(REPO_ROOT)
            unknown = sorted(set(parsed) - top_level)
            if unknown:
                problems.append(
                    f"{rel}:{first_line}: health payload shows field(s) "
                    f"{', '.join(repr(u) for u in unknown)} that /api/health does not return"
                )
            for row in parsed.get("privacy_checklist") or []:
                if not isinstance(row, dict):
                    continue
                bad = sorted(set(row) - item_keys)
                if bad:
                    problems.append(
                        f"{rel}:{first_line}: privacy_checklist entry "
                        f"{row.get('item', '<unnamed>')!r} uses key(s) "
                        f"{', '.join(repr(b) for b in bad)}; the endpoint emits "
                        f"{', '.join(sorted(item_keys))}"
                    )
    return problems


def check_result_references() -> list[str]:
    """Every ``*.json`` path in the docs must resolve, and be tracked if it is
    an evaluation result file."""
    problems: list[str] = []
    tracked = _tracked_files()
    basenames = _result_json_basenames()

    for doc in iter_docs():
        text = doc.read_text(encoding="utf-8", errors="replace")
        doc_dir = doc.parent
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in JSON_REF_RE.finditer(line):
                token = match.group(0).strip("`'\"()[],;")
                if "/" in token:
                    candidates = [
                        REPO_ROOT / token.lstrip("./"),
                        doc_dir / token,
                        REPO_ROOT / "backend" / token,
                    ]
                    resolved = next((c for c in candidates if c.is_file()), None)
                    if resolved is None:
                        problems.append(
                            f"{doc.relative_to(REPO_ROOT)}:{line_no}: references "
                            f"'{token}', which does not exist"
                        )
                        continue
                else:
                    if token in EXEMPT_BARE_JSON:
                        continue
                    if token not in basenames:
                        problems.append(
                            f"{doc.relative_to(REPO_ROOT)}:{line_no}: references "
                            f"'{token}', which is not a file under "
                            f"{RESULTS_ROOT.relative_to(REPO_ROOT)} (generic config "
                            f"names belong in EXEMPT_BARE_JSON)"
                        )
                        continue
                    resolved = next(RESULTS_ROOT.rglob(token))

                rel = resolved.relative_to(REPO_ROOT).as_posix()
                results_rel = RESULTS_ROOT.relative_to(REPO_ROOT).as_posix()
                if rel.startswith(results_rel + "/") and rel not in tracked:
                    problems.append(
                        f"{doc.relative_to(REPO_ROOT)}:{line_no}: cites {rel}, "
                        f"which exists locally but is not committed; a fresh clone "
                        f"cannot obtain the evidence"
                    )
    return problems


def run_all_checks() -> list[str]:
    """Return a list of human-readable problems; empty means the docs agree."""
    problems = check_test_counts()
    problems.extend(check_result_references())
    problems.extend(check_health_contract())
    return problems


def main() -> int:
    problems = run_all_checks()
    if problems:
        print("Documentation drift detected:\n")
        for problem in problems:
            print(f"  - {problem}")
        print(f"\n{len(problems)} problem(s).")
        return 1
    print(
        f"Documentation is consistent: hermetic test count {hermetic_test_count()}, "
        f"all cited result files exist and are committed, and every documented "
        f"/api/health field is real."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
