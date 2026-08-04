"""
Scores src/brain/boundary_guard.check_injection_signal() against the
"prompt_injection" category cases in adversarial_cases.jsonl.

Kept as a separate script from adversarial_boundary_eval.py rather than
folded into it: that harness scores risk_classifier.py/boundary_guard.check()
verdicts (local/external/destructive/boundary:X), a fundamentally different
kind of output than this check's binary "did this fire or not" signal.
Conflating the two would make both harder to read and reason about.

Usage:
    python -m eval.injection_signal_eval
"""
from __future__ import annotations

import json
from pathlib import Path

from src.brain.boundary_guard import check_injection_signal

_CASES_PATH = Path(__file__).parent / "adversarial_cases.jsonl"


def _load_cases() -> list[dict]:
    with open(_CASES_PATH) as f:
        return [
            json.loads(line) for line in f
            if line.strip() and json.loads(line).get("category") == "prompt_injection"
        ]


def run() -> tuple[int, int, list[dict]]:
    cases = _load_cases()
    correct = 0
    failures = []
    for case in cases:
        signal = check_injection_signal(case["step"])
        got = signal is not None
        expected = case["expected_injection_signal"]
        if got == expected:
            correct += 1
        else:
            failures.append({**case, "got_signal": got})
    return correct, len(cases), failures


def main() -> None:
    correct, total, failures = run()
    print(f"prompt_injection signal accuracy: {correct}/{total}")
    for f in failures:
        print(f"  [{f['id']}] expected_injection_signal={f['expected_injection_signal']} "
              f"got={f['got_signal']} -- {f['note']}")


if __name__ == "__main__":
    main()
