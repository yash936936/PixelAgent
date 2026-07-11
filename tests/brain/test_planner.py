import json

import pytest

from src.brain.planner import LocalPlanner, _parse_step


def test_local_planner_returns_parsed_step():
    valid_json = json.dumps(
        {"action": "click", "description": "click it", "target_type": "web", "params": {"selector": "#a"}}
    )
    planner = LocalPlanner(generate_fn=lambda system, prompt: valid_json)
    step = planner.next_step("do the thing", {"url": "x"}, [])
    assert step["action"] == "click"


def test_local_planner_passes_system_and_user_content():
    captured = {}

    def fake_generate(system_prompt, user_content):
        captured["system"] = system_prompt
        captured["user"] = json.loads(user_content)
        return json.dumps({"action": "done", "description": "d", "target_type": "web", "params": {}})

    planner = LocalPlanner(generate_fn=fake_generate)
    planner.next_step("go somewhere", {"url": "x"}, [{"step": {"action": "navigate"}}])

    assert "Pixel" in captured["system"]
    assert captured["user"]["instruction"] == "go somewhere"
    assert captured["user"]["current_state"] == {"url": "x"}


def test_local_planner_raises_on_invalid_json():
    planner = LocalPlanner(generate_fn=lambda system, prompt: "not json")
    with pytest.raises(ValueError):
        planner.next_step("do the thing", {}, [])


def test_local_planner_raises_on_missing_required_field():
    incomplete = json.dumps({"action": "click"})
    planner = LocalPlanner(generate_fn=lambda system, prompt: incomplete)
    with pytest.raises(ValueError):
        planner.next_step("do the thing", {}, [])


def test_parse_step_shared_by_both_backends():
    valid_json = json.dumps(
        {"action": "done", "description": "finished", "target_type": "web", "params": {}}
    )
    assert _parse_step(valid_json)["action"] == "done"
