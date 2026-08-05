"""
Phase 10 (docs/PHASES.md) — mines real task trace logs for genuine risk-
classification correction signal: cases where a human actually disagreed
with or edited the agent's risk handling (denied/edited gate decisions),
or where a step was never classified at all (the fixed
unclassified_or_missing_risk() -- see docs/DECISIONS.md's 2026-08-02 entry
for the real bug found and fixed there before this tool could trust it).

This is a bridge step before real LoRA training (training/prepare_dataset.py,
training/train_lora.py), which remains blocked on a GPU and enough real
usage data regardless of this tool. What this DOES do: surface real,
human-sourced correction examples that could expand
src/brain/semantic_matcher.py's exemplar banks -- a cheap, same-day
improvement, the same category of thing Phase 6 already did with
hand-written exemplars, just now informed by what real usage actually
produced instead of only guessed paraphrases.

Deliberately does NOT auto-modify semantic_matcher.py. A human should
review each mined candidate before it becomes a permanent exemplar --
auto-injecting unreviewed real user data into a keyword/exemplar bank
risks baking in noise, an isolated mistake, or something environment-
specific (see the real "false positives from replan-retry log lines" bug
this exact tool's underlying query had, found and fixed before this
module existed).

Usage:
    python -m training.mine_corrections [log_dir]
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from src.observability.trace_replay import TraceReplay, find_trace_files


@dataclass
class CorrectionCandidate:
    source: str  # "denied_gate" | "edited_gate" | "unclassified_risk"
    trace_file: str
    step_num: int | None
    action: str | None
    description: str | None
    detail: str  # human-readable context, e.g. what risk tier, what was edited to


def mine_corrections(log_dir: Path) -> list[CorrectionCandidate]:
    """Scans every task_*.jsonl trace in log_dir for real correction signal.
    Three sources, each a genuinely different kind of "the agent's risk
    handling didn't match what actually happened":

    - denied_gate: a human denied a step the risk classifier gated --
      real evidence about what a real user considers risky enough to
      refuse, independent of what tier the keyword/semantic layer assigned.
    - edited_gate: a human approved but changed the step first -- softer
      signal than a denial, but still real evidence the original step's
      framing needed correction.
    - unclassified_risk: a step that reached execution with no risk tier
      at all (after the 2026-08-02 fix excluding 'done' actions and
      replan-retry noise) -- a genuine classifier gap, not evasion, but
      still worth knowing about.
    """
    candidates: list[CorrectionCandidate] = []

    for trace_path in find_trace_files(log_dir):
        try:
            replay = TraceReplay.load(trace_path)
        except Exception:  # noqa: BLE001 - a malformed/partial trace shouldn't kill the whole scan
            continue

        for event in replay.denied_gate_decisions():
            step = event.step or {}
            candidates.append(CorrectionCandidate(
                source="denied_gate", trace_file=trace_path.name, step_num=event.step_num,
                action=step.get("action"), description=step.get("description"),
                detail=f"risk={event.risk} was denied by the user",
            ))

        for event in replay.edited_gate_decisions():
            step = event.step or {}
            candidates.append(CorrectionCandidate(
                source="edited_gate", trace_file=trace_path.name, step_num=event.step_num,
                action=step.get("action"), description=step.get("description"),
                detail=f"risk={event.risk}, user edited the step before approving",
            ))

        for event in replay.unclassified_or_missing_risk():
            step = event.step or {}
            candidates.append(CorrectionCandidate(
                source="unclassified_risk", trace_file=trace_path.name, step_num=event.step_num,
                action=step.get("action"), description=step.get("description"),
                detail="reached a final outcome with no risk tier ever recorded",
            ))

    return candidates


def main() -> None:
    log_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./logs")
    candidates = mine_corrections(log_dir)

    if not candidates:
        print(
            f"No correction candidates found in {log_dir} -- either no traces exist yet, or "
            "every real task so far completed with no denied/edited gate decisions and no "
            "risk-classification gaps. This is a real, honest finding, not a tool failure: it "
            "means there's nothing new to add to semantic_matcher.py's exemplar banks from "
            "this data yet. Re-run this after more varied real usage accumulates."
        )
        return

    print(f"Found {len(candidates)} correction candidate(s) in {log_dir}:\n")
    for c in candidates:
        print(f"[{c.source}] {c.trace_file} step {c.step_num}: action={c.action!r}")
        print(f"    description: {c.description!r}")
        print(f"    {c.detail}\n")
    print(
        "Review each of these by hand before adding any as a new exemplar phrase in "
        "src/brain/semantic_matcher.py -- this tool surfaces candidates, it does not decide "
        "for you which ones represent a genuine, generalizable pattern worth encoding."
    )


if __name__ == "__main__":
    main()
