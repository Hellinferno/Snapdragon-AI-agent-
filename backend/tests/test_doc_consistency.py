"""Keeps the documentation from drifting away from the code it describes.

The implementation lives in ``scripts/check_docs.py`` so it can also be run
directly (``python -m scripts.check_docs``) when reviewing docs by hand. Two
classes of claim are machine-checked:

* the size of the hermetic test suite — four documents once simultaneously
  advertised 95, 79, 37 and 31 tests;
* paths of evaluation result files cited as evidence — ``DEMO.md`` used to cite
  a result file that was never committed.

Collecting the suite runs pytest in a subprocess, which adds a few seconds. That
cost is accepted because a guard that cannot notice the suite growing is exactly
the guard that let the four-way count drift happen in the first place.
"""

from __future__ import annotations

from scripts.check_docs import (
    check_health_contract,
    check_result_references,
    check_test_counts,
    hermetic_test_count,
)


def test_documented_test_count_matches_the_suite() -> None:
    problems = check_test_counts()
    assert not problems, (
        "documented test counts disagree with the collected suite:\n  "
        + "\n  ".join(problems)
    )


def test_cited_result_files_exist_and_are_committed() -> None:
    problems = check_result_references()
    assert not problems, (
        "documents cite evaluation evidence a reader cannot obtain:\n  "
        + "\n  ".join(problems)
    )


def test_documented_health_payload_uses_real_fields() -> None:
    problems = check_health_contract()
    assert not problems, (
        "documents describe a runtime telemetry contract the endpoint does not "
        "implement:\n  " + "\n  ".join(problems)
    )


def test_hermetic_count_is_plausible() -> None:
    """Guards the guard: a collection failure must not look like agreement."""
    count = hermetic_test_count()
    assert count > 50, (
        f"only {count} hermetic tests were collected, which means pytest is not "
        f"seeing the suite; the doc checks above would be vacuous"
    )
