"""
src/observability/beta_report.py — Phase 18: the feedback/crash-report channel.

Per docs/PHASES.md's Phase 18 file table: "Some way for beta users to report a
failure with enough context (trace log excerpt) to be actionable, without exposing
their full screenshot history." This module is that channel -- a CLI a beta tester
runs after hitting something worth reporting, which builds one shareable Markdown
report for one task and (optionally, opt-in only) a small number of screenshots
from that same task.

Design choices, stated plainly:
- Built on top of audit_export.py (Phase 17), not a new trace parser -- the
  legible per-action summary that module already produces is exactly what a
  developer triaging a beta report needs, and reusing it means this module has
  no independent trace-format logic to keep in sync.
- Screenshots are NEVER attached automatically. A beta user's screenshot history
  can contain anything that was on their screen -- unrelated open tabs, personal
  messages, account details having nothing to do with the actual bug. Phase 18's
  own file-table wording ("without exposing their full screenshot history") is
  read here as the strict, safe interpretation: zero screenshots by default, and
  even with --include-screenshots, only the ones referenced by the SPECIFIC task
  being reported (never a full logs/ directory dump), with an explicit printed
  warning before anything is copied.
- Redaction is inherited, not reinvented: the underlying trace log already went
  through logger.py's _redact_step() key-based redaction before it was ever
  written to disk (Phase 4) -- this module trusts and builds on that rather than
  attempting a second, independent redaction pass, which would risk giving a
  false sense of double-safety while actually just duplicating the same
  keyword-matching limitation described in PRIVACY.md.
- No network call, no telemetry, no auto-upload. This produces a local file the
  beta tester chooses to share (paste into an issue, attach to an email) --
  matching this project's existing "no data leaves the machine unless the user
  explicitly sends it" posture (PRIVACY.md).

Usage:
    # Build a report for the most recent task in a log directory
    python -m src.observability.beta_report logs/

    # Build a report for one specific task file
    python -m src.observability.beta_report logs/task_20260816T120000_ab12cd.jsonl

    # Also copy that task's own screenshots alongside the report (opt-in, prints
    # a warning, never includes any other task's screenshots)
    python -m src.observability.beta_report logs/ --include-screenshots

    # Add free-text notes describing what went wrong, from the tester's own words
    python -m src.observability.beta_report logs/ --notes "clicked submit twice"
"""
from __future__ import annotations

import argparse
import platform
import shutil
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path

from src.observability.audit_export import build_audit_trail, render_markdown
from src.observability.trace_replay import TraceLoadError, TraceReplay, find_trace_files


def _pixel_version() -> str:
    """Reads the installed package version via importlib.metadata rather than
    parsing pyproject.toml directly -- works correctly whether this is a real
    pip-installed build (the case that matters for a real beta tester) or a
    from-source dev checkout (falls back to "unknown (source checkout)" rather
    than raising, since a report shouldn't fail to generate over this)."""
    try:
        return _pkg_version("pixel-agent")
    except PackageNotFoundError:
        return "unknown (source checkout, not pip-installed)"


def _system_info() -> dict:
    """Deliberately narrow: OS/Python/Pixel version only -- exactly what a
    developer triaging a report needs to reproduce an environment-specific
    bug (e.g. "only fails on Windows 11 with Python 3.13"), nothing that
    identifies the person or machine beyond that (no hostname, no username,
    no IP, no MAC address)."""
    return {
        "pixel_version": _pixel_version(),
        "os": platform.platform(),
        "python_version": platform.python_version(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_report(
    log_path: Path,
    output_dir: Path,
    notes: str | None = None,
    include_screenshots: bool = False,
) -> Path:
    """Builds one Markdown report (plus an optional screenshots/ subfolder)
    for a single task's trace, written under output_dir. Returns the path to
    the generated Markdown file.

    log_path may be a specific task_*.jsonl file, or a directory (in which
    case the most recent trace in it is used, same convention as
    trace_replay.py's own find_trace_files()).
    """
    log_path = Path(log_path)
    if log_path.is_dir():
        candidates = find_trace_files(log_path)
        if not candidates:
            raise TraceLoadError(f"No task_*.jsonl trace files found in {log_path}")
        log_path = candidates[0]

    replay = TraceReplay.load(log_path)
    entries = build_audit_trail(replay)
    audit_markdown = render_markdown(replay, entries)

    info = _system_info()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Beta feedback report",
        "",
        "Generated by `src/observability/beta_report.py` (Phase 18). This report was built "
        "entirely on this machine -- nothing here has been sent anywhere automatically. "
        "Share it however you'd normally report a bug (paste into an issue, attach to an "
        "email).",
        "",
        "## Environment",
        "",
        f"- **Pixel version:** {info['pixel_version']}",
        f"- **OS:** {info['os']}",
        f"- **Python version:** {info['python_version']}",
        f"- **Report generated:** {info['generated_at']}",
        "",
    ]

    if notes:
        lines.extend(["## What the tester reported", "", notes.strip(), ""])

    lines.extend(["## Task trace", "", audit_markdown])

    screenshots = replay.screenshots()
    screenshot_note = (
        "No screenshots are included in this report by default -- see PRIVACY.md for why. "
        f"{len(screenshots)} screenshot(s) were referenced by this task; re-run with "
        "`--include-screenshots` to attach copies of ONLY this task's own screenshots."
        if not include_screenshots
        else f"{len(screenshots)} screenshot(s) from this task were copied into "
        "`screenshots/` alongside this report (opt-in, this task's own trace only)."
    )
    lines.extend(["", "## Screenshots", "", screenshot_note])

    report_path = output_dir / f"beta_report_{log_path.stem}.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    if include_screenshots and screenshots:
        shots_dir = output_dir / "screenshots"
        shots_dir.mkdir(exist_ok=True)
        copied = 0
        for shot_path_str in screenshots:
            shot_path = Path(shot_path_str)
            if shot_path.is_file():
                shutil.copy2(shot_path, shots_dir / shot_path.name)
                copied += 1
        print(
            f"WARNING: copied {copied} screenshot(s) from this task into {shots_dir} -- "
            "review them before sharing this report, since a screenshot can show more than "
            "the task's own params (see PRIVACY.md).",
            file=sys.stderr,
        )

    return report_path


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("log_path", help="A task_*.jsonl file, or a log directory (uses the most recent trace).")
    parser.add_argument("--out", default="beta_reports", help="Output directory for the generated report.")
    parser.add_argument("--notes", default=None, help="Free-text description of what went wrong, in your own words.")
    parser.add_argument(
        "--include-screenshots", action="store_true",
        help="Also copy this task's own screenshots into the report folder. Off by default -- see PRIVACY.md.",
    )
    args = parser.parse_args()

    try:
        report_path = build_report(
            Path(args.log_path),
            Path(args.out),
            notes=args.notes,
            include_screenshots=args.include_screenshots,
        )
    except TraceLoadError as exc:
        print(f"Could not build a report: {exc}", file=sys.stderr)
        raise SystemExit(1)

    print(f"Beta feedback report written to {report_path}")
    print("Review it before sharing -- redaction is best-effort, not a guarantee (see PRIVACY.md).")


if __name__ == "__main__":
    _main()
