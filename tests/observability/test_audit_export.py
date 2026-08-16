import json

from src.observability.audit_export import (
    AuditEntry,
    build_audit_trail,
    export_task,
    render_markdown,
)
from src.observability.trace_replay import TraceReplay


def _write_trace(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _basic_trace(tmp_path, name="task_audit_1.jsonl"):
    p = tmp_path / name
    _write_trace(
        p,
        [
            {"type": "event", "step_num": 0, "payload": "task started", "timestamp": "t0"},
            {
                "type": "step",
                "step_num": 1,
                "step": {"action": "navigate", "description": "Open github.com"},
                "outcome": {"ok": True},
                "risk": "local",
                "llm_call": True,
                "timestamp": "t1",
            },
            {
                "type": "gate_decision",
                "step_num": 2,
                "step": {"action": "click", "description": "Star the repo"},
                "risk": "external",
                "verdict": "approved",
                "edited": False,
                "timestamp": "t2a",
            },
            {
                "type": "step",
                "step_num": 2,
                "step": {"action": "click", "description": "Star the repo"},
                "outcome": {"ok": True},
                "risk": "external",
                "llm_call": True,
                "timestamp": "t2b",
            },
            {
                "type": "gate_decision",
                "step_num": 3,
                "step": {"action": "click", "description": "Delete the repo"},
                "risk": "destructive",
                "verdict": "denied",
                "edited": False,
                "timestamp": "t3a",
            },
            {
                "type": "step",
                "step_num": 3,
                "step": {"action": "click", "description": "Delete the repo"},
                "outcome": {"status": "hard_boundary_blocked", "error": "denied by gate"},
                "risk": "destructive",
                "llm_call": False,
                "timestamp": "t3b",
            },
            {
                "type": "task_complete",
                "result": {"success": True, "status": "done"},
                "audit": {"step_count": 3, "llm_calls": 2, "est_cost": 0.0123},
                "timestamp": "t4",
            },
        ],
    )
    return p


def test_build_audit_trail_one_entry_per_step(tmp_path):
    replay = TraceReplay.load(_basic_trace(tmp_path))
    entries = build_audit_trail(replay)

    assert len(entries) == 3
    assert [e.step_num for e in entries] == [1, 2, 3]
    assert all(isinstance(e, AuditEntry) for e in entries)


def test_local_step_no_approval_needed(tmp_path):
    replay = TraceReplay.load(_basic_trace(tmp_path))
    entries = build_audit_trail(replay)

    local_entry = entries[0]
    assert local_entry.action == "navigate"
    assert local_entry.risk == "local"
    assert local_entry.approval is None
    assert local_entry.outcome == "done"


def test_approved_external_step_folds_in_gate_decision(tmp_path):
    replay = TraceReplay.load(_basic_trace(tmp_path))
    entries = build_audit_trail(replay)

    external_entry = entries[1]
    assert external_entry.action == "click"
    assert external_entry.risk == "external"
    assert external_entry.approval == "approved"
    assert external_entry.outcome == "done"


def test_denied_destructive_step_reports_blocked(tmp_path):
    replay = TraceReplay.load(_basic_trace(tmp_path))
    entries = build_audit_trail(replay)

    destructive_entry = entries[2]
    assert destructive_entry.approval == "denied"
    assert destructive_entry.outcome == "blocked"
    assert destructive_entry.detail is not None
    assert "safety boundary" in destructive_entry.detail


def test_edited_step_reports_edited_not_approved(tmp_path):
    p = tmp_path / "task_edited.jsonl"
    _write_trace(
        p,
        [
            {
                "type": "gate_decision",
                "step_num": 1,
                "step": {"action": "type", "description": "Send message"},
                "risk": "external",
                "verdict": "approved",
                "edited": True,
                "timestamp": "t1a",
            },
            {
                "type": "step",
                "step_num": 1,
                "step": {"action": "type", "description": "Send message (edited)"},
                "outcome": {"ok": True},
                "risk": "external",
                "llm_call": True,
                "timestamp": "t1b",
            },
        ],
    )
    replay = TraceReplay.load(p)
    entries = build_audit_trail(replay)

    assert len(entries) == 1
    assert entries[0].approval == "edited"


def test_only_final_entry_per_step_num_used_on_retry(tmp_path):
    """A step that errors, gets replanned, and retried writes multiple log
    lines for the same step_num -- the audit trail should reflect only the
    final, settled outcome, same convention as trace_replay.py's own
    unclassified_or_missing_risk()."""
    p = tmp_path / "task_retry.jsonl"
    _write_trace(
        p,
        [
            {
                "type": "step",
                "step_num": 1,
                "step": {"action": "click", "description": "Click submit"},
                "outcome": {"status": "error", "error": "element not found"},
                "risk": "local",
                "llm_call": True,
                "timestamp": "t1a",
            },
            {
                "type": "step",
                "step_num": 1,
                "step": {"action": "click", "description": "Click submit (retry)"},
                "outcome": {"ok": True},
                "risk": "local",
                "llm_call": True,
                "timestamp": "t1b",
            },
        ],
    )
    replay = TraceReplay.load(p)
    entries = build_audit_trail(replay)

    assert len(entries) == 1
    assert entries[0].outcome == "done"
    assert entries[0].description == "Click submit (retry)"


def test_operational_limit_exceeded_maps_to_stopped(tmp_path):
    p = tmp_path / "task_limit.jsonl"
    _write_trace(
        p,
        [
            {
                "type": "step",
                "step_num": 1,
                "step": {"action": "click", "description": "Do a thing"},
                "outcome": {"status": "operational_limit_exceeded", "error": "cost ceiling hit"},
                "risk": "local",
                "llm_call": True,
                "timestamp": "t1",
            },
        ],
    )
    replay = TraceReplay.load(p)
    entries = build_audit_trail(replay)

    assert entries[0].outcome == "stopped"
    assert "operational safety limit" in entries[0].detail


def test_audit_entry_to_line_is_readable():
    entry = AuditEntry(
        step_num=1,
        timestamp="2026-08-16T00:00:00Z",
        action="click",
        description="Star the repo",
        risk="external",
        approval="approved",
        outcome="done",
    )
    line = entry.to_line()
    assert "Star the repo" in line
    assert "external risk" in line
    assert "approved" in line
    assert "done" in line


def test_render_markdown_includes_summary_and_actions(tmp_path):
    replay = TraceReplay.load(_basic_trace(tmp_path))
    md = render_markdown(replay)

    assert "# Audit trail" in md
    assert "## Actions" in md
    assert "Open github.com" in md
    assert "Star the repo" in md
    assert "Delete the repo" in md
    assert "$0.0123" in md


def test_render_markdown_with_no_steps_says_so(tmp_path):
    p = tmp_path / "task_empty_steps.jsonl"
    _write_trace(p, [{"type": "event", "step_num": 0, "payload": "task started", "timestamp": "t0"}])
    replay = TraceReplay.load(p)
    md = render_markdown(replay)

    assert "No actions were recorded" in md


def test_export_task_writes_file(tmp_path):
    log_path = _basic_trace(tmp_path)
    out_path = tmp_path / "audit.md"

    markdown = export_task(log_path, out_path)

    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8") == markdown
    assert "# Audit trail" in markdown


def test_export_task_without_output_path_just_returns(tmp_path):
    log_path = _basic_trace(tmp_path)
    markdown = export_task(log_path)
    assert "# Audit trail" in markdown
