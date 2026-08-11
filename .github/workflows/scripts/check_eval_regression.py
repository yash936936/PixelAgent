#!/usr/bin/env python3
"""check_eval_regression.py — Phase 14 CI regression gate.

Parses eval/adversarial_boundary_eval.py's stdout for its overall accuracy
percentage and fails (non-zero exit) if it's below a given floor.

FIX (2026-08-11): the original regex expected a line like
"Overall accuracy: NN.N%". The script's REAL output format, confirmed against
actual CI output, is:

    Overall: 25/36 (69%)

Updated to match that real format instead of a guessed one. This is
DELIBERATELY a loose regression check, not the real deployment gate --
eval/README.md's actual thresholds (recall >= 0.95 for evasive_destructive/
boundary_evasion, >= 0.90 for the other two categories) apply only to a trained
RISK_MODEL_BACKEND=local model, which does not exist yet per docs/STATUS.md's
Phase 10 entry (honest zero result -- no real correction data exists yet).
"""

import argparse
import re
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_output_file", help="Path to captured stdout from adversarial_boundary_eval.py")
    parser.add_argument("--min-overall", type=float, required=True, help="Minimum acceptable overall accuracy, as a percentage (e.g. 70 for 70%%)")
    args = parser.parse_args()

    with open(args.eval_output_file, "r", encoding="utf-8") as f:
        output = f.read()

    # Real format: "Overall: 25/36 (69%)" -- match the parenthesized percentage.
    match = re.search(r"Overall:\s*\d+/\d+\s*\((\d+(?:\.\d+)?)%\)", output)
    if not match:
        print(
            "ERROR: could not find an 'Overall: N/M (P%)' line in eval output. "
            "eval/adversarial_boundary_eval.py's print format may have changed again -- "
            "update the regex in check_eval_regression.py, don't silently ignore this "
            "failure.",
            file=sys.stderr,
        )
        return 2

    overall = float(match.group(1))
    print(f"Parsed overall accuracy: {overall}% (floor: {args.min_overall}%)")

    if overall < args.min_overall:
        print(
            f"REGRESSION: overall accuracy {overall}% is below the {args.min_overall}% "
            f"floor. This does not mean the change is necessarily wrong -- it means it "
            f"changed the semantic layer's eval score, which should be a deliberate, "
            f"reviewed decision (per this project's docs/DECISIONS.md convention), not "
            f"an unnoticed side effect.",
            file=sys.stderr,
        )
        return 1

    print("OK: no regression detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
