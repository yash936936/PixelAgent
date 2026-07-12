import json
import sqlite3
from pathlib import Path

from training.prepare_dataset import build_planner_examples, build_risk_model_examples


def test_build_risk_model_examples_excludes_boundary_cases(tmp_path):
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text(
        "\n".join(
            [
                json.dumps({"id": "a", "step": {"action": "click", "description": "delete it"}, "expected_risk": "destructive"}),
                json.dumps({"id": "b", "step": {"action": "click", "description": "bypass captcha"}, "expected_risk": "boundary:captcha_bot_detection_bypass"}),
            ]
        )
    )
    examples = build_risk_model_examples(cases_path)
    assert len(examples) == 1
    assistant_content = json.loads(examples[0]["messages"][-1]["content"])
    assert assistant_content["risk"] == "destructive"


def test_build_risk_model_examples_message_shape(tmp_path):
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text(
        json.dumps({"id": "a", "step": {"action": "click", "description": "x", "params": {}}, "expected_risk": "local"})
    )
    examples = build_risk_model_examples(cases_path)
    assert len(examples) == 1
    roles = [m["role"] for m in examples[0]["messages"]]
    assert roles == ["system", "user", "assistant"]


def test_build_planner_examples_empty_db_returns_empty_list(tmp_path):
    missing_db = tmp_path / "does_not_exist.db"
    assert build_planner_examples(missing_db) == []


def test_build_planner_examples_from_real_schema(tmp_path):
    db_path = tmp_path / "episodic.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE episodes (id INTEGER PRIMARY KEY, instruction TEXT, "
        "normalized_instruction TEXT, steps_json TEXT, status TEXT, edited INTEGER, created_at REAL)"
    )
    steps = [{"step": {"action": "navigate", "description": "go", "target_type": "web", "params": {}}}]
    conn.execute(
        "INSERT INTO episodes (instruction, normalized_instruction, steps_json, status, edited, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("open x.com", "open x.com", json.dumps(steps), "done", 0, 0.0),
    )
    conn.commit()
    conn.close()

    examples = build_planner_examples(db_path)
    assert len(examples) == 1
    assert json.loads(examples[0]["messages"][-1]["content"])["action"] == "navigate"


def test_build_planner_examples_ignores_non_done_episodes(tmp_path):
    db_path = tmp_path / "episodic.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE episodes (id INTEGER PRIMARY KEY, instruction TEXT, "
        "normalized_instruction TEXT, steps_json TEXT, status TEXT, edited INTEGER, created_at REAL)"
    )
    conn.execute(
        "INSERT INTO episodes (instruction, normalized_instruction, steps_json, status, edited, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("failed task", "failed task", json.dumps([]), "failed", 0, 0.0),
    )
    conn.commit()
    conn.close()

    assert build_planner_examples(db_path) == []
