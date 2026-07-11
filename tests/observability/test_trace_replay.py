import json

import pytest

from src.observability.trace_replay import (
    TraceLoadError,
    TraceReplay,
    find_trace_files,
)


def _write_trace(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(TraceLoadError):
        TraceReplay.load(tmp_path / "task_nope.jsonl")


def test_load_empty_file_raises(tmp_path):
    p = tmp_path / "task_empty.jsonl"
    p.write_text("")
    with pytest.raises(TraceLoadError):
        TraceReplay.load(p)


def test_load_malformed_json_raises(tmp_path):
    p = tmp_path / "task_bad.jsonl"
    p.write_text('{"type": "step"}\nnot json\n')
    with pytest.raises(TraceLoadError):
        TraceReplay.load(p)


def test_load_and_step_forward(tmp_path):
    p = tmp_path / "task_1.jsonl"
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
                "step": {"action": "click", "description": "Star repo"},
                "risk": "external",
                "verdict": "approved",
                "edited": False,
                "timestamp": "t2",
            },
            {
                "type": "task_complete",
                "result": {"success": True},
                "audit": {"step_count": 2, "llm_calls": 1, "est_cost": 0.0},
                "timestamp": "t3",
            },
        ],
    )

    replay = TraceReplay.load(p)
    assert len(replay) == 4

    replay.reset()
    first = replay.step_forward()
    assert first.type == "event"
    second = replay.step_forward()
    assert second.type == "step"
    assert second.risk == "local"
    third = replay.step_forward()
    assert third.type == "gate_decision"
    assert third.verdict == "approved"
    fourth = replay.step_forward()
    assert fourth.type == "task_complete"
    assert replay.step_forward() is None


def test_step_backward_and_current(tmp_path):
    p = tmp_path / "task_2.jsonl"
    _write_trace(
        p,
        [
            {"type": "event", "step_num": 0, "payload": "start"},
            {"type": "step", "step_num": 1, "step": {"action": "a"}, "outcome": {}, "risk": "local"},
        ],
    )
    replay = TraceReplay.load(p)
    replay.step_forward()
    replay.step_forward()
    assert replay.current().type == "step"
    back = replay.step_backward()
    assert back.type == "event"
    assert replay.step_backward() is None  # walked off the start


def test_jump_to_out_of_range_raises(tmp_path):
    p = tmp_path / "task_3.jsonl"
    _write_trace(p, [{"type": "event", "step_num": 0, "payload": "start"}])
    replay = TraceReplay.load(p)
    with pytest.raises(IndexError):
        replay.jump_to(5)


def test_unclassified_or_missing_risk(tmp_path):
    p = tmp_path / "task_4.jsonl"
    _write_trace(
        p,
        [
            {"type": "step", "step_num": 1, "step": {"action": "a"}, "outcome": {}, "risk": "local"},
            {"type": "step", "step_num": 2, "step": {"action": "b"}, "outcome": {}, "risk": None},
        ],
    )
    replay = TraceReplay.load(p)
    gaps = replay.unclassified_or_missing_risk()
    assert len(gaps) == 1
    assert gaps[0].step_num == 2


def test_edited_and_denied_gate_decisions(tmp_path):
    p = tmp_path / "task_5.jsonl"
    _write_trace(
        p,
        [
            {
                "type": "gate_decision", "step_num": 1, "step": {"action": "send"},
                "risk": "external", "verdict": "approved", "edited": True,
            },
            {
                "type": "gate_decision", "step_num": 2, "step": {"action": "delete"},
                "risk": "destructive", "verdict": "denied", "edited": False,
            },
        ],
    )
    replay = TraceReplay.load(p)
    edited = replay.edited_gate_decisions()
    denied = replay.denied_gate_decisions()
    assert len(edited) == 1 and edited[0].step_num == 1
    assert len(denied) == 1 and denied[0].step_num == 2


def test_screenshots_deduplicated_in_order(tmp_path):
    p = tmp_path / "task_6.jsonl"
    _write_trace(
        p,
        [
            {"type": "step", "step_num": 1, "step": {"screenshot": "a.png"}, "outcome": {}, "risk": "local"},
            {"type": "step", "step_num": 2, "step": {}, "outcome": {"screenshot": "b.png"}, "risk": "local"},
            {"type": "step", "step_num": 3, "step": {"screenshot": "a.png"}, "outcome": {}, "risk": "local"},
        ],
    )
    replay = TraceReplay.load(p)
    assert replay.screenshots() == ["a.png", "b.png"]


def test_task_complete_returns_last_matching_event(tmp_path):
    p = tmp_path / "task_7.jsonl"
    _write_trace(
        p,
        [
            {"type": "step", "step_num": 1, "step": {}, "outcome": {}, "risk": "local"},
            {"type": "task_complete", "result": {"success": True}, "audit": {}},
        ],
    )
    replay = TraceReplay.load(p)
    tc = replay.task_complete()
    assert tc is not None
    assert tc.raw["result"]["success"] is True


def test_find_trace_files_sorted_most_recent_first(tmp_path):
    (tmp_path / "task_20260101T000000.jsonl").write_text('{"type": "event"}\n')
    (tmp_path / "task_20260201T000000.jsonl").write_text('{"type": "event"}\n')
    (tmp_path / "not_a_trace.txt").write_text("ignore me")

    files = find_trace_files(tmp_path)
    assert len(files) == 2
    assert files[0].name == "task_20260201T000000.jsonl"


def test_find_trace_files_missing_dir_returns_empty(tmp_path):
    assert find_trace_files(tmp_path / "does_not_exist") == []


def test_summary_line_variants(tmp_path):
    p = tmp_path / "task_8.jsonl"
    _write_trace(
        p,
        [
            {"type": "step", "step_num": 1, "step": {"action": "click"}, "outcome": {"ok": True}, "risk": "local"},
            {"type": "gate_decision", "step_num": 2, "step": {"action": "delete"}, "risk": "destructive", "verdict": "denied", "edited": False},
            {"type": "event", "step_num": 0, "payload": "replay started"},
            {"type": "task_complete", "result": {"success": True}, "audit": {}},
        ],
    )
    replay = TraceReplay.load(p)
    lines = [e.summary_line() for e in replay]
    assert "STEP 1" in lines[0]
    assert "GATE step=2" in lines[1]
    assert "EVENT step=0" in lines[2]
    assert "TASK_COMPLETE" in lines[3]
