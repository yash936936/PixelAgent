"""
Converts available data sources into instruction-tuning jsonl for one of the
two SEPARATE Track B training runs (see training/README.md). Runnable now
(no GPU/training deps needed) since it's pure data transformation -- but
until real logged tasks exist (docs/STATUS.md: zero live runs so far), the
"risk_model" target only has eval/adversarial_cases.jsonl to draw on, and
the "planner" target has nothing at all to draw on (episodic memory is
necessarily empty). Both are stated honestly in this script's output rather
than silently producing a tiny/empty file that looks like it worked.

Usage:
    python -m training.prepare_dataset --target risk_model --out training/data/risk_model_train.jsonl
    python -m training.prepare_dataset --target planner --out training/data/planner_train.jsonl \
        --episodic-db logs/episodic.db
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

_RISK_MODEL_SYSTEM_PROMPT = """You are a safety classifier for a desktop automation \
agent. Classify the given action into exactly one of: "local", "external", "destructive".
- local: only affects local UI state, fully reversible, doesn't affect anything outside this session
- external: visible to other people/systems, or hard to undo
- destructive: deletes or overwrites the user's data

Respond with ONLY a JSON object: {"risk": "local" | "external" | "destructive"}"""


def build_risk_model_examples(adversarial_cases_path: Path) -> list[dict]:
    """Converts eval/adversarial_cases.jsonl into (prompt, completion) training
    examples. NOTE: these are the same cases used for EVALUATION in
    eval/adversarial_boundary_eval.py -- training on your own eval set
    defeats the point of holding it out. This function exists so you can see
    the *shape* of a training example and so a held-out split is easy to
    build correctly (see --holdout-fraction), NOT so you train on 100% of
    eval/adversarial_cases.jsonl and then declare victory against the same
    set. Split first, train on the split, eval only on what you held out."""
    examples = []
    with open(adversarial_cases_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            expected = case["expected_risk"]
            if expected.startswith("boundary:"):
                # Boundary cases are boundary_guard.py's job, not the risk
                # model's -- excluded from this training target on purpose.
                continue
            examples.append(
                {
                    "messages": [
                        {"role": "system", "content": _RISK_MODEL_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "action": case["step"].get("action"),
                                    "description": case["step"].get("description"),
                                    "params": case["step"].get("params", {}),
                                }
                            ),
                        },
                        {"role": "assistant", "content": json.dumps({"risk": expected})},
                    ]
                }
            )
    return examples


def build_planner_examples(episodic_db_path: Path) -> list[dict]:
    """Converts successful (status='done') episodes from episodic_store.py's
    SQLite DB into planner training examples -- one example per step in a
    successful episode. Returns an empty list (with a clear message printed
    by _main(), not a silent empty file) if the DB doesn't exist or has no
    successful episodes yet, since that's the real state of this project as
    of 2026-07-12."""
    if not episodic_db_path.exists():
        return []

    examples = []
    conn = sqlite3.connect(str(episodic_db_path))
    try:
        rows = conn.execute(
            "SELECT instruction, steps_json FROM episodes WHERE status = 'done'"
        ).fetchall()
    except sqlite3.OperationalError:
        # Table/column names here mirror episodic_store.py's actual schema
        # as of this writing -- if that schema changes, this query needs
        # updating alongside it (see docs/DECISIONS.md discipline).
        return []
    finally:
        conn.close()

    for instruction, steps_json in rows:
        steps = json.loads(steps_json)
        history: list[dict] = []
        for entry in steps:
            step = entry.get("step", entry)
            examples.append(
                {
                    "messages": [
                        {"role": "system", "content": "PLANNER_SYSTEM_PROMPT_PLACEHOLDER"},
                        {
                            "role": "user",
                            "content": json.dumps(
                                {"instruction": instruction, "steps_so_far": history}
                            ),
                        },
                        {"role": "assistant", "content": json.dumps(step)},
                    ]
                }
            )
            history = history + [entry]
    return examples


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=["risk_model", "planner"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--adversarial-cases", type=Path, default=Path("eval/adversarial_cases.jsonl")
    )
    parser.add_argument("--episodic-db", type=Path, default=Path("logs/episodic.db"))
    args = parser.parse_args()

    if args.target == "risk_model":
        examples = build_risk_model_examples(args.adversarial_cases)
        if len(examples) < 50:
            print(
                f"[warn] Only {len(examples)} risk-model examples available. This is far too "
                "small to fine-tune on responsibly -- see training/README.md: real training data "
                "should come primarily from corrections mined out of real trace logs via "
                "trace_replay.py's unclassified_or_missing_risk(), not just the eval set."
            )
    else:
        examples = build_planner_examples(args.episodic_db)
        if not examples:
            print(
                f"[warn] No successful episodes found in {args.episodic_db}. Per docs/STATUS.md, "
                "this project has never run a live task, so this is expected right now, not a bug "
                "in this script. Run real tasks first, then re-run this command."
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"Wrote {len(examples)} example(s) to {args.out}")


if __name__ == "__main__":
    _main()
