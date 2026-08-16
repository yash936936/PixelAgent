"""
End-user audit trail export (docs/PHASES.md Phase 17).

trace_replay.py's TraceReplay is a developer debugging tool -- it exposes raw
JSONL events and expects familiarity with this project's own internal event
types ("step" / "gate_decision" / "event" / "task_complete") and field names
("risk", "verdict", "edited"). A second party who has trusted this agent with
their accounts needs a legible "what did it do, when, why" answer, not that.

This module builds on TraceReplay (never re-parses the raw trace itself) and
produces a small, ordered list of AuditEntry records -- one per user-visible
action -- plus a human-readable Markdown rendering. Kept dependency-free
(stdlib only), same convention as trace_replay.py, so it can be imported and
unit-tested without pulling in Playwright/pyautogui/the LLM SDK.

This module is read-only, same as trace_replay.py: it never re-executes any
action, never re-contacts the LLM, and never re-opens the confirmation gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.observability.trace_replay import TraceEvent, TraceReplay, find_trace_files


@dataclass
class AuditEntry:
    """One legible, user-facing line: what the agent did (or asked about),
    when, at what risk level, and what happened. Deliberately a much smaller
    surface than TraceEvent -- a developer trace has multiple log lines per
    step (retries, gate decisions, outcomes); an audit entry collapses those
    into the one thing an end user actually cares about: did the agent do
    this, and how did it go."""

    step_num: int | None
    timestamp: str | None
    action: str
    description: str
    risk: str | None
    approval: str | None  # "approved" / "denied" / "edited" / None (no gate needed)
    outcome: str  # "done" / "failed" / "blocked" / "pending"
    detail: str | None = None  # error message or blocked-reason, if any

    def to_line(self) -> str:
        risk_label = f" [{self.risk} risk]" if self.risk else ""
        approval_label = f" ({self.approval})" if self.approval else ""
        when = self.timestamp or "unknown time"
        line = f"- **{when}** — {self.description}{risk_label}{approval_label}: **{self.outcome}**"
        if self.detail:
            line += f" — {self.detail}"
        return line


def _outcome_status(event: TraceEvent) -> tuple[str, str | None]:
    """Maps a step event's outcome dict to a plain-English (status, detail)
    pair. Mirrors orchestrator.py's own status vocabulary
    ("hard_boundary_blocked", "replan_exhausted", "error",
    "operational_limit_exceeded", etc.) but translates each into wording an
    end user -- not a developer reading orchestrator.py's source -- can
    understand without cross-referencing this project's internals."""
    outcome = event.outcome or {}
    status = outcome.get("status")
    error = outcome.get("error")

    if status is None:
        ok = outcome.get("ok")
        if ok is True:
            return "done", None
        if ok is False:
            return "failed", error
        return "pending", None

    if status == "hard_boundary_blocked":
        return "blocked", "refused: crosses a hard safety boundary (see TERMS.md)"
    if status in ("replan_exhausted", "replay_replan_exhausted"):
        return "failed", "could not find a working approach after multiple attempts"
    if status == "operational_limit_exceeded":
        return "stopped", "an operational safety limit (cost/time/concurrency) was hit"
    if status in ("error", "replay_error"):
        return "failed", error
    if status in ("verification_screenshot_failed",):
        return "warning", "could not verify the result with a screenshot"
    return status, error


def build_audit_trail(replay: TraceReplay) -> list[AuditEntry]:
    """Builds the ordered, legible audit trail for one task's trace.

    One AuditEntry per step_num that reached a final, settled outcome --
    same "last entry per step_num wins" convention trace_replay.py's own
    unclassified_or_missing_risk() uses, since intermediate retry log lines
    are internal bookkeeping, not independently meaningful actions from an
    end user's point of view. A step's matching gate_decision (if any) is
    folded in as the entry's approval field, rather than kept as a separate
    line -- an end user asking "what did it do" wants one line per action,
    not a raw pairing of a plan with its approval.
    """
    last_step_per_num: dict[int | None, TraceEvent] = {}
    for e in replay.steps():
        last_step_per_num[e.step_num] = e

    gate_by_step: dict[int | None, TraceEvent] = {}
    for e in replay.gate_decisions():
        gate_by_step[e.step_num] = e  # last gate decision wins if a step was replanned+re-gated

    entries: list[AuditEntry] = []
    for step_num in sorted(
        (k for k in last_step_per_num if k is not None), key=lambda x: (x is None, x)
    ):
        event = last_step_per_num[step_num]
        step = event.step or {}
        action = step.get("action", "?")
        description = step.get("description") or action
        risk = event.risk

        gate = gate_by_step.get(step_num)
        approval = None
        if gate is not None:
            if gate.edited:
                approval = "edited"
            elif gate.verdict == "approved":
                approval = "approved"
            elif gate.verdict == "denied":
                approval = "denied"
            else:
                approval = gate.verdict

        outcome_status, detail = _outcome_status(event)

        entries.append(
            AuditEntry(
                step_num=step_num,
                timestamp=event.timestamp,
                action=action,
                description=description,
                risk=risk,
                approval=approval,
                outcome=outcome_status,
                detail=detail,
            )
        )

    return entries


def render_markdown(replay: TraceReplay, entries: list[AuditEntry] | None = None) -> str:
    """Renders a full Markdown audit-trail document for one task's trace --
    the thing an end user (or the end user's own auditor/lawyer) could
    actually read, per Phase 17's success criterion ("an audit trail an end
    user could actually read"). Not raw JSONL."""
    if entries is None:
        entries = build_audit_trail(replay)

    complete = replay.task_complete()
    result = (complete.raw.get("result") if complete else None) or {}
    audit_summary = (complete.raw.get("audit") if complete else None) or {}

    lines = [
        f"# Audit trail — {replay.log_path.name}",
        "",
        "Generated from a local trace log by `src/observability/audit_export.py`. "
        "This is a human-readable summary of what the agent did during this task, "
        "not the raw developer trace log (see `docs/DEBUG.md`/`trace_replay.py` for that).",
        "",
    ]

    if result:
        outcome = result.get("status", result.get("outcome", "unknown"))
        lines.append(f"**Final outcome:** {outcome}")
    if audit_summary:
        steps = audit_summary.get("step_count")
        llm_calls = audit_summary.get("llm_calls")
        cost = audit_summary.get("est_cost")
        cost_str = f"${cost:.4f}" if isinstance(cost, (int, float)) else "unknown"
        lines.append(f"**Steps taken:** {steps}  **LLM calls:** {llm_calls}  **Estimated cost:** {cost_str}")
    lines.append("")

    lines.append("## Actions")
    lines.append("")
    if not entries:
        lines.append("*No actions were recorded for this task.*")
    else:
        for entry in entries:
            lines.append(entry.to_line())

    lines.append("")
    screenshots = replay.screenshots()
    if screenshots:
        lines.append(f"## Screenshots referenced ({len(screenshots)})")
        lines.append("")
        lines.append(
            "Full-frame captures taken during this task, for verification. "
            "See `PRIVACY.md` for how long these are retained and how they're stored."
        )
        for path in screenshots:
            lines.append(f"- `{path}`")
        lines.append("")

    return "\n".join(lines)


def export_task(log_path: Path, output_path: Path | None = None) -> str:
    """Loads a trace file and writes (or just returns, if output_path is
    None) its Markdown audit trail. Convenience wrapper for the CLI below
    and for callers (e.g. a future GUI "export audit trail" button) that
    just want one call."""
    replay = TraceReplay.load(log_path)
    markdown = render_markdown(replay)
    if output_path is not None:
        output_path = Path(output_path)
        output_path.write_text(markdown, encoding="utf-8")
    return markdown


def _main() -> None:
    """CLI: `python -m src.observability.audit_export <log_dir_or_file> [output.md]`

    Mirrors trace_replay.py's own _main() conventions: a bare directory picks
    the most recent task_*.jsonl; a specific file is used directly."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.observability.audit_export <log_dir_or_file> [output.md]")
        raise SystemExit(1)

    target = Path(sys.argv[1])
    if target.is_dir():
        files = find_trace_files(target)
        if not files:
            print(f"No task_*.jsonl trace files found in {target}")
            raise SystemExit(1)
        log_path = files[0]
    else:
        log_path = target

    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    markdown = export_task(log_path, output_path)
    if output_path is None:
        print(markdown)
    else:
        print(f"Audit trail written to {output_path}")


if __name__ == "__main__":
    _main()
