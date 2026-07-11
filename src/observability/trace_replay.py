"""
Developer trace-replay tool (docs/PHASES.md Phase 5, Part 5).

Lets a developer step through a full past task trace — plan, screenshots,
gate decisions, outcomes — written by logger.py's log_step() / log_event() /
log_gate_decision() / log_task_complete() to a `<log_dir>/task_*.jsonl` file.

This module is read-only with respect to the trace: it never re-executes any
action, never re-contacts the LLM, and never re-opens the confirmation gate.
It exists purely so a human can inspect what happened, in order, for
debugging (docs/TRD.md: "MUST support replaying a full task trace for
debugging") and to satisfy Phase 5's success criterion that "full trace
replay works for any logged task."

Kept dependency-free (stdlib only) so it can be imported and unit-tested
without pulling in Playwright/pyautogui/the LLM SDK, matching the project's
existing pattern (see risk_classifier.py's module docstring) of keeping
pure-logic modules import-light.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


class TraceLoadError(RuntimeError):
    """Raised when a trace file is missing, empty, or contains a line that
    isn't valid JSON. Fails loud rather than silently skipping malformed
    entries, since a debugging tool that quietly drops records is worse than
    one that refuses to run."""


@dataclass
class TraceEvent:
    """One line of a task's .jsonl trace, normalized for replay."""

    index: int
    type: str
    timestamp: str | None
    raw: dict

    # Convenience accessors — return None rather than raising when the field
    # doesn't apply to this event's type, so a developer can probe any event
    # uniformly while stepping through the trace.
    @property
    def step_num(self) -> int | None:
        return self.raw.get("step_num")

    @property
    def step(self) -> dict | None:
        return self.raw.get("step")

    @property
    def outcome(self) -> dict | None:
        return self.raw.get("outcome")

    @property
    def risk(self) -> str | None:
        return self.raw.get("risk")

    @property
    def verdict(self) -> str | None:
        return self.raw.get("verdict")

    @property
    def edited(self) -> bool | None:
        return self.raw.get("edited")

    @property
    def screenshot_path(self) -> str | None:
        # Screenshot references are carried inside "step" or "outcome"
        # payloads by whichever module logged them (perception/action), so
        # check both rather than assuming a fixed top-level key.
        for container in (self.raw.get("step"), self.raw.get("outcome")):
            if isinstance(container, dict) and container.get("screenshot"):
                return container["screenshot"]
        return None

    def summary_line(self) -> str:
        """One-line human-readable summary for CLI stepping."""
        if self.type == "step":
            action = (self.step or {}).get("action", "?")
            risk = self.risk or "?"
            ok = (self.outcome or {}).get("ok")
            return f"[{self.index}] STEP {self.step_num} risk={risk} action={action} ok={ok}"
        if self.type == "gate_decision":
            action = (self.step or {}).get("action", "?")
            return (
                f"[{self.index}] GATE step={self.step_num} risk={self.risk} "
                f"verdict={self.verdict} edited={self.edited} action={action}"
            )
        if self.type == "event":
            return f"[{self.index}] EVENT step={self.step_num} {self.raw.get('payload', self.raw)}"
        if self.type == "task_complete":
            return f"[{self.index}] TASK_COMPLETE result={self.raw.get('result')}"
        return f"[{self.index}] {self.type.upper()} {self.raw}"


@dataclass
class TraceReplay:
    """Loads one task's .jsonl log file and lets a developer step through it.

    Usage:
        replay = TraceReplay.load(Path("logs/task_20260711T120000.jsonl"))
        for event in replay.events:
            print(event.summary_line())

        # or step interactively:
        replay.reset()
        while (event := replay.step_forward()) is not None:
            print(event.summary_line())
    """

    log_path: Path
    events: list[TraceEvent] = field(default_factory=list)
    _cursor: int = -1

    @classmethod
    def load(cls, log_path: Path) -> "TraceReplay":
        log_path = Path(log_path)
        if not log_path.exists():
            raise TraceLoadError(f"Trace file not found: {log_path}")

        lines = log_path.read_text(encoding="utf-8").splitlines()
        if not lines:
            raise TraceLoadError(f"Trace file is empty: {log_path}")

        events: list[TraceEvent] = []
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                raise TraceLoadError(
                    f"Malformed JSON on line {i + 1} of {log_path}: {e}"
                ) from e
            events.append(
                TraceEvent(
                    index=len(events),
                    type=record.get("type", "unknown"),
                    timestamp=record.get("timestamp"),
                    raw=record,
                )
            )

        return cls(log_path=log_path, events=events)

    # -- interactive stepping -------------------------------------------------

    def reset(self) -> None:
        self._cursor = -1

    def step_forward(self) -> TraceEvent | None:
        if self._cursor + 1 >= len(self.events):
            return None
        self._cursor += 1
        return self.events[self._cursor]

    def step_backward(self) -> TraceEvent | None:
        if self._cursor <= 0:
            self._cursor = -1
            return None
        self._cursor -= 1
        return self.events[self._cursor]

    def current(self) -> TraceEvent | None:
        if 0 <= self._cursor < len(self.events):
            return self.events[self._cursor]
        return None

    def jump_to(self, index: int) -> TraceEvent:
        if not (0 <= index < len(self.events)):
            raise IndexError(f"index {index} out of range (0..{len(self.events) - 1})")
        self._cursor = index
        return self.events[index]

    # -- structured queries used by both a CLI and docs/DEBUG.md's protocol --

    def steps(self) -> list[TraceEvent]:
        return [e for e in self.events if e.type == "step"]

    def gate_decisions(self) -> list[TraceEvent]:
        return [e for e in self.events if e.type == "gate_decision"]

    def unclassified_or_missing_risk(self) -> list[TraceEvent]:
        """Every step event with no risk recorded at all -- a gap that Phase
        5's success criterion ("no unclassified/misclassified risk cases")
        is checking for directly."""
        return [e for e in self.steps() if not e.risk]

    def edited_gate_decisions(self) -> list[TraceEvent]:
        return [e for e in self.gate_decisions() if e.edited]

    def denied_gate_decisions(self) -> list[TraceEvent]:
        return [e for e in self.gate_decisions() if e.verdict == "denied"]

    def task_complete(self) -> TraceEvent | None:
        for e in reversed(self.events):
            if e.type == "task_complete":
                return e
        return None

    def screenshots(self) -> list[str]:
        """All screenshot paths referenced anywhere in the trace, in order,
        de-duplicated while preserving first-seen order."""
        seen: dict[str, None] = {}
        for e in self.events:
            path = e.screenshot_path
            if path:
                seen.setdefault(path, None)
        return list(seen.keys())

    def __iter__(self) -> Iterator[TraceEvent]:
        return iter(self.events)

    def __len__(self) -> int:
        return len(self.events)


def find_trace_files(log_dir: Path) -> list[Path]:
    """Lists every task_*.jsonl trace in log_dir, most recent first, so a
    developer (or a CLI built on top of this module) can pick a task without
    having to remember its exact timestamped filename."""
    log_dir = Path(log_dir)
    if not log_dir.exists():
        return []
    return sorted(log_dir.glob("task_*.jsonl"), reverse=True)


def _main() -> None:
    """Minimal CLI: `python -m src.observability.trace_replay <log_dir_or_file>`
    prints every event's summary line for the chosen (or most recent) trace.
    This is a debugging convenience, not a user-facing entry point --
    src/main.py is unaffected."""
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./logs")

    if target.is_dir():
        candidates = find_trace_files(target)
        if not candidates:
            print(f"No task_*.jsonl trace files found in {target}")
            return
        log_path = candidates[0]
        print(f"Most recent trace: {log_path}")
    else:
        log_path = target

    replay = TraceReplay.load(log_path)
    for event in replay:
        print(event.summary_line())

    gaps = replay.unclassified_or_missing_risk()
    if gaps:
        print(f"\n⚠ {len(gaps)} step(s) with no recorded risk classification:")
        for e in gaps:
            print(f"  {e.summary_line()}")

    complete = replay.task_complete()
    if complete:
        print(f"\n{complete.summary_line()}")


if __name__ == "__main__":
    _main()
