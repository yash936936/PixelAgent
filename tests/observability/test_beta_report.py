import json

import pytest

from src.observability.beta_report import build_report
from src.observability.trace_replay import TraceLoadError


def _write_trace(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _trace_with_screenshot(tmp_path, name="task_beta_1.jsonl"):
    p = tmp_path / name
    _write_trace(
        p,
        [
            {
                "type": "step",
                "step_num": 1,
                "step": {"action": "click", "description": "Open settings"},
                "outcome": {"ok": True, "screenshot": str(tmp_path / "shot1.png")},
                "risk": "local",
                "llm_call": True,
                "timestamp": "t1",
            },
            {
                "type": "step",
                "step_num": 2,
                "step": {"action": "click", "description": "Submit form"},
                "outcome": {"status": "error", "error": "button not found"},
                "risk": "local",
                "llm_call": True,
                "timestamp": "t2",
            },
        ],
    )
    # A real screenshot file so --include-screenshots has something real to copy.
    (tmp_path / "shot1.png").write_bytes(b"fake png bytes")
    return p


def test_build_report_from_specific_file(tmp_path):
    log_path = _trace_with_screenshot(tmp_path)
    out_dir = tmp_path / "reports"

    report_path = build_report(log_path, out_dir)

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# Beta feedback report" in content
    assert "Open settings" in content
    assert "Submit form" in content


def test_build_report_includes_environment_info(tmp_path):
    log_path = _trace_with_screenshot(tmp_path)
    report_path = build_report(log_path, tmp_path / "reports")
    content = report_path.read_text(encoding="utf-8")

    assert "## Environment" in content
    assert "Pixel version:" in content
    assert "OS:" in content
    assert "Python version:" in content


def test_build_report_includes_notes_when_given(tmp_path):
    log_path = _trace_with_screenshot(tmp_path)
    report_path = build_report(log_path, tmp_path / "reports", notes="the submit button did nothing")
    content = report_path.read_text(encoding="utf-8")

    assert "## What the tester reported" in content
    assert "the submit button did nothing" in content


def test_build_report_omits_notes_section_when_not_given(tmp_path):
    log_path = _trace_with_screenshot(tmp_path)
    report_path = build_report(log_path, tmp_path / "reports")
    content = report_path.read_text(encoding="utf-8")

    assert "## What the tester reported" not in content


def test_screenshots_not_copied_by_default(tmp_path):
    log_path = _trace_with_screenshot(tmp_path)
    out_dir = tmp_path / "reports"
    report_path = build_report(log_path, out_dir)
    content = report_path.read_text(encoding="utf-8")

    assert not (out_dir / "screenshots").exists()
    assert "No screenshots are included in this report by default" in content


def test_screenshots_copied_only_when_opted_in(tmp_path):
    log_path = _trace_with_screenshot(tmp_path)
    out_dir = tmp_path / "reports"

    report_path = build_report(log_path, out_dir, include_screenshots=True)
    content = report_path.read_text(encoding="utf-8")

    shots_dir = out_dir / "screenshots"
    assert shots_dir.exists()
    assert (shots_dir / "shot1.png").exists()
    assert "copied into" in content


def test_directory_input_uses_most_recent_trace(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    _write_trace(
        log_dir / "task_20260101T000000_aaaaaa.jsonl",
        [{"type": "step", "step_num": 1, "step": {"action": "click", "description": "old task"},
          "outcome": {"ok": True}, "risk": "local", "llm_call": True, "timestamp": "t0"}],
    )
    _write_trace(
        log_dir / "task_20260816T000000_bbbbbb.jsonl",
        [{"type": "step", "step_num": 1, "step": {"action": "click", "description": "new task"},
          "outcome": {"ok": True}, "risk": "local", "llm_call": True, "timestamp": "t1"}],
    )

    report_path = build_report(log_dir, tmp_path / "reports")
    content = report_path.read_text(encoding="utf-8")

    assert "new task" in content
    assert "old task" not in content


def test_empty_log_dir_raises_clear_error(tmp_path):
    empty_dir = tmp_path / "empty_logs"
    empty_dir.mkdir()

    with pytest.raises(TraceLoadError):
        build_report(empty_dir, tmp_path / "reports")


def test_report_filename_is_stable_and_tied_to_source_trace(tmp_path):
    log_path = _trace_with_screenshot(tmp_path, name="task_20260816T120000_ff00aa.jsonl")
    report_path = build_report(log_path, tmp_path / "reports")

    assert report_path.name == "beta_report_task_20260816T120000_ff00aa.md"


def test_report_never_sees_unredacted_secrets_only_what_was_already_on_disk(tmp_path):
    """Confirms this module doesn't attempt (and doesn't need) a second
    redaction pass -- it only ever reads what logger.py's own _redact_step()
    already wrote to disk (Phase 4). A value already masked as
    ***REDACTED*** in the source trace should appear that way, verbatim, in
    the report -- never "un-redacted" back to a real value, since this
    module has no access to one in the first place."""
    p = tmp_path / "task_redacted.jsonl"
    _write_trace(
        p,
        [
            {
                "type": "step",
                "step_num": 1,
                "step": {"action": "type", "description": "Log in", "params": {"password": "***REDACTED***"}},
                "outcome": {"ok": True},
                "risk": "local",
                "llm_call": True,
                "timestamp": "t1",
            },
        ],
    )
    report_path = build_report(p, tmp_path / "reports")
    content = report_path.read_text(encoding="utf-8")

    assert "Log in" in content
