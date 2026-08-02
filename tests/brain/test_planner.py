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


def test_local_planner_retries_once_on_truncated_json_then_succeeds():
    """Real failure mode found by Phase 7's first live run (docs/DECISIONS.md
    2026-08-01): a transiently truncated/malformed generation must not crash
    the whole task if a retry would succeed."""
    calls = {"count": 0}

    def flaky_generate(system_prompt, user_content):
        calls["count"] += 1
        if calls["count"] == 1:
            return '{\n  "action": "navigate",\n  "description": "truncated'  # malformed
        return json.dumps(
            {"action": "navigate", "description": "d", "target_type": "web", "params": {"url": "x"}}
        )

    planner = LocalPlanner(generate_fn=flaky_generate)
    step = planner.next_step("do the thing", {}, [])
    assert step["action"] == "navigate"
    assert calls["count"] == 2


def test_local_planner_raises_after_two_consecutive_failures():
    """Bounded retry -- a persistent failure (e.g. a real outage) must
    still surface as an error rather than retrying forever."""
    planner = LocalPlanner(generate_fn=lambda system, prompt: "still not json")
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


# --- fix for gap: est_cost was always 0.0, nothing computed a real cost ---

from types import SimpleNamespace  # noqa: E402

from src.brain.planner import HostedLLMPlanner, estimate_cost_usd  # noqa: E402


def test_estimate_cost_usd_basic_math():
    cost = estimate_cost_usd(input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == pytest.approx(0.075 + 0.30)


def test_estimate_cost_usd_zero_tokens_is_zero():
    assert estimate_cost_usd(0, 0) == 0.0


def test_hosted_planner_records_real_cost_from_usage_metadata(monkeypatch):
    class FakeResponse:
        text = json.dumps({"action": "done", "description": "d", "target_type": "web", "params": {}})
        usage_metadata = SimpleNamespace(prompt_token_count=1000, candidates_token_count=200)

    class FakeModels:
        def generate_content(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("src.brain.planner.genai.Client", FakeClient)

    planner = HostedLLMPlanner(api_key="fake", model="gemini-2.5-flash")
    planner.next_step("do it", {}, [])

    expected = estimate_cost_usd(1000, 200)
    assert planner.last_call_cost == pytest.approx(expected)
    assert planner.last_call_cost > 0.0


def test_hosted_planner_cost_zero_when_no_usage_metadata(monkeypatch):
    class FakeResponse:
        text = json.dumps({"action": "done", "description": "d", "target_type": "web", "params": {}})
        usage_metadata = None

    class FakeModels:
        def generate_content(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("src.brain.planner.genai.Client", FakeClient)

    planner = HostedLLMPlanner(api_key="fake", model="gemini-2.5-flash")
    planner.next_step("do it", {}, [])
    assert planner.last_call_cost == 0.0


def test_hosted_planner_retries_once_on_truncated_json_then_succeeds(monkeypatch):
    responses = [
        SimpleNamespace(text='{"action": "navigate", "description": "truncated', usage_metadata=None),
        SimpleNamespace(
            text=json.dumps(
                {"action": "navigate", "description": "d", "target_type": "web", "params": {"url": "x"}}
            ),
            usage_metadata=None,
        ),
    ]

    class FakeModels:
        def __init__(self):
            self.call_count = 0

        def generate_content(self, **kwargs):
            resp = responses[self.call_count]
            self.call_count += 1
            return resp

    fake_models = FakeModels()

    class FakeClient:
        def __init__(self, api_key):
            self.models = fake_models

    monkeypatch.setattr("src.brain.planner.genai.Client", FakeClient)

    planner = HostedLLMPlanner(api_key="fake", model="gemini-2.5-flash")
    step = planner.next_step("do it", {}, [])
    assert step["action"] == "navigate"
    assert fake_models.call_count == 2
    class FakeResponse:
        text = json.dumps({"risk": "destructive", "reason": "test"})
        usage_metadata = None

    class FakeModels:
        def generate_content(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("src.brain.planner.genai.Client", FakeClient)

    planner = HostedLLMPlanner(api_key="fake", model="gemini-2.5-flash")
    raw = planner._generate_fn("system prompt", "user content")
    assert json.loads(raw)["risk"] == "destructive"
