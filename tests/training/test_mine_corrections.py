import json
from pathlib import Path

from training.mine_corrections import CorrectionCandidate, mine_corrections


def _write_trace(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")


def test_mine_corrections_finds_denied_gate_decisions(tmp_path):
    _write_trace(
        tmp_path / "task_1.jsonl",
        [
            {"type": "gate_decision", "step_num": 1, "step": {"action": "click", "description": "delete the repo"},
             "risk": "destructive", "verdict": "denied", "edited": False},
        ],
    )
    candidates = mine_corrections(tmp_path)
    assert len(candidates) == 1
    assert candidates[0].source == "denied_gate"
    assert candidates[0].action == "click"
    assert "denied" in candidates[0].detail


def test_mine_corrections_finds_edited_gate_decisions(tmp_path):
    _write_trace(
        tmp_path / "task_2.jsonl",
        [
            {"type": "gate_decision", "step_num": 1, "step": {"action": "type", "description": "send the email"},
             "risk": "external", "verdict": "approved", "edited": True},
        ],
    )
    candidates = mine_corrections(tmp_path)
    assert len(candidates) == 1
    assert candidates[0].source == "edited_gate"


def test_mine_corrections_finds_genuinely_unclassified_risk(tmp_path):
    _write_trace(
        tmp_path / "task_3.jsonl",
        [
            {"type": "step", "step_num": 1, "step": {"action": "click", "description": "mystery action"},
             "outcome": {"status": "error"}, "risk": None},
        ],
    )
    candidates = mine_corrections(tmp_path)
    assert len(candidates) == 1
    assert candidates[0].source == "unclassified_risk"


def test_mine_corrections_excludes_done_steps_and_replan_noise(tmp_path):
    """Real behavior found live on 2026-08-02 (docs/DECISIONS.md, Phase
    10): this must inherit trace_replay.py's fixed
    unclassified_or_missing_risk() semantics, not re-introduce the same
    false-positive-on-real-data bug at this layer."""
    _write_trace(
        tmp_path / "task_4.jsonl",
        [
            {"type": "step", "step_num": 1, "step": {"action": "done", "description": "finished"},
             "outcome": {"status": "task_complete"}, "risk": None},
            {"type": "step", "step_num": 2, "step": {"action": "click", "description": "retry me"},
             "outcome": {"status": "replanned"}, "risk": None},
            {"type": "step", "step_num": 2, "step": {"action": "click", "description": "retry me"},
             "outcome": {"status": "executed"}, "risk": "local"},
        ],
    )
    candidates = mine_corrections(tmp_path)
    assert candidates == []


def test_mine_corrections_returns_empty_list_for_clean_traces(tmp_path):
    """The honest, real result found against actual Phase 7 trace data:
    zero denied/edited gate decisions, and (after the logging fix) zero
    genuine unclassified-risk gaps either -- this must be represented as
    a clean empty list, not an error or a fabricated finding."""
    _write_trace(
        tmp_path / "task_clean.jsonl",
        [
            {"type": "step", "step_num": 1, "step": {"action": "navigate", "description": "go to site"},
             "outcome": {"status": "executed"}, "risk": "local"},
            {"type": "gate_decision", "step_num": 2, "step": {"action": "click", "description": "click star"},
             "risk": "external", "verdict": "approved", "edited": False},
            {"type": "step", "step_num": 2, "step": {"action": "click", "description": "click star"},
             "outcome": {"status": "executed"}, "risk": "external"},
        ],
    )
    assert mine_corrections(tmp_path) == []


def test_mine_corrections_scans_multiple_trace_files(tmp_path):
    _write_trace(
        tmp_path / "task_a.jsonl",
        [{"type": "gate_decision", "step_num": 1, "step": {"action": "a", "description": "a"},
          "risk": "external", "verdict": "denied", "edited": False}],
    )
    _write_trace(
        tmp_path / "task_b.jsonl",
        [{"type": "gate_decision", "step_num": 1, "step": {"action": "b", "description": "b"},
          "risk": "external", "verdict": "denied", "edited": False}],
    )
    candidates = mine_corrections(tmp_path)
    assert len(candidates) == 2
    assert {c.trace_file for c in candidates} == {"task_a.jsonl", "task_b.jsonl"}


def test_mine_corrections_returns_empty_for_missing_log_dir(tmp_path):
    assert mine_corrections(tmp_path / "does_not_exist") == []


def test_mine_corrections_skips_malformed_trace_files_without_crashing(tmp_path):
    (tmp_path / "task_broken.jsonl").write_text("not valid json at all", encoding="utf-8")
    _write_trace(
        tmp_path / "task_ok.jsonl",
        [{"type": "gate_decision", "step_num": 1, "step": {"action": "a", "description": "a"},
          "risk": "external", "verdict": "denied", "edited": False}],
    )
    candidates = mine_corrections(tmp_path)
    assert len(candidates) == 1
    assert candidates[0].trace_file == "task_ok.jsonl"


def test_correction_candidate_is_a_plain_dataclass():
    c = CorrectionCandidate(
        source="denied_gate", trace_file="x.jsonl", step_num=1, action="click",
        description="d", detail="detail",
    )
    assert c.source == "denied_gate"
