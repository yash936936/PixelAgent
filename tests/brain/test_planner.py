import json

import pytest

from src.brain.planner import LocalPlanner, SYSTEM_PROMPT, _parse_step


def test_system_prompt_documents_hotkey_action_preferred_for_start_menu():
    """Real fix, docs/DECISIONS.md 2026-08-02: every live desktop run so
    far needed a mid-task replan to recover from an unreliable OCR click
    on the Start button. hotkey was already wired into action_router.py
    but never mentioned in the prompt, so the planner never knew it could
    use it. Pins that the prompt now documents it."""
    assert '"hotkey"' in SYSTEM_PROMPT
    assert '"keys": ["win"]' in SYSTEM_PROMPT
    assert "Start menu" in SYSTEM_PROMPT


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

    planner = HostedLLMPlanner(api_key="fake", model="gemini-3.5-flash-lite")
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

    planner = HostedLLMPlanner(api_key="fake", model="gemini-3.5-flash-lite")
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

    planner = HostedLLMPlanner(api_key="fake", model="gemini-3.5-flash-lite")
    step = planner.next_step("do it", {}, [])
    assert step["action"] == "navigate"
    assert fake_models.call_count == 2


def _rate_limit_error(retry_delay_seconds: int = 1):
    """Builds a genai_errors.ClientError shaped like the real 429 response
    body seen live on 2026-08-01, including the RetryInfo the fix reads
    the suggested backoff from."""
    from google.genai import errors as genai_errors

    response_json = {
        "error": {
            "code": 429,
            "message": "You exceeded your current quota...",
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.RetryInfo",
                    "retryDelay": f"{retry_delay_seconds}s",
                }
            ],
        }
    }
    return genai_errors.ClientError(429, response_json, None)


def test_hosted_planner_retries_after_rate_limit_then_succeeds(monkeypatch):
    """Real bug found live on 2026-08-01 (docs/DECISIONS.md): a 429
    RESOURCE_EXHAUSTED error crashed the whole task with an unhandled
    traceback -- the parse-failure retry above doesn't catch this at all,
    since it's a completely different exception type. Must back off
    (respecting the server's suggested delay) and retry instead."""
    monkeypatch.setattr("src.brain.planner.time.sleep", lambda *_: None)  # keep the test instant

    success_response = SimpleNamespace(
        text=json.dumps(
            {"action": "navigate", "description": "d", "target_type": "web", "params": {"url": "x"}}
        ),
        usage_metadata=None,
    )

    call_count = {"n": 0}

    class FakeModels:
        def generate_content(self, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise _rate_limit_error()
            return success_response

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("src.brain.planner.genai.Client", FakeClient)

    planner = HostedLLMPlanner(api_key="fake", model="gemini-3.5-flash-lite")
    step = planner.next_step("do it", {}, [])
    assert step["action"] == "navigate"
    assert call_count["n"] == 2


def test_hosted_planner_raises_after_exhausting_rate_limit_retries(monkeypatch):
    """A persistent rate-limit failure (e.g. quota genuinely exhausted for
    the day) must eventually surface as a real error, not retry forever."""
    monkeypatch.setattr("src.brain.planner.time.sleep", lambda *_: None)

    call_count = {"n": 0}

    class FakeModels:
        def generate_content(self, **kwargs):
            call_count["n"] += 1
            raise _rate_limit_error()

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("src.brain.planner.genai.Client", FakeClient)

    from google.genai import errors as genai_errors

    planner = HostedLLMPlanner(api_key="fake", model="gemini-3.5-flash-lite")
    with pytest.raises(genai_errors.ClientError):
        planner.next_step("do it", {}, [])
    assert call_count["n"] == 2  # default rate_limit_max_attempts, no more no less


def test_hosted_planner_rate_limit_attempts_is_configurable_to_fail_fast(monkeypatch):
    """Real fix, docs/DECISIONS.md 2026-08-01: the original hardcoded
    3-attempt/uncapped-backoff retry was found live to compound into 10+
    minutes of wait on a heavily-throttled free-tier key across a
    multi-step task. rate_limit_max_attempts=1 must disable the retry
    entirely -- no sleep, no second attempt, the real error surfaces
    immediately."""
    monkeypatch.setattr("src.brain.planner.time.sleep", lambda *_: (_ for _ in ()).throw(
        AssertionError("must never sleep when rate_limit_max_attempts=1")
    ))

    from google.genai import errors as genai_errors

    call_count = {"n": 0}

    class FakeModels:
        def generate_content(self, **kwargs):
            call_count["n"] += 1
            raise _rate_limit_error()

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("src.brain.planner.genai.Client", FakeClient)

    planner = HostedLLMPlanner(api_key="fake", model="gemini-3.5-flash-lite", rate_limit_max_attempts=1)
    with pytest.raises(genai_errors.ClientError):
        planner.next_step("do it", {}, [])
    assert call_count["n"] == 1  # zero retries -- fails on the very first attempt


def test_hosted_planner_rate_limit_backoff_is_capped(monkeypatch):
    """rate_limit_max_backoff_seconds must cap whatever the server's own
    RetryInfo suggests, not just pass it through uncapped -- found live
    that the free tier can suggest ~30s+ per attempt."""
    slept_for = []
    monkeypatch.setattr("src.brain.planner.time.sleep", lambda seconds: slept_for.append(seconds))

    success_response = SimpleNamespace(
        text=json.dumps(
            {"action": "navigate", "description": "d", "target_type": "web", "params": {"url": "x"}}
        ),
        usage_metadata=None,
    )
    call_count = {"n": 0}

    class FakeModels:
        def generate_content(self, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise _rate_limit_error(retry_delay_seconds=45)  # server suggests 45s
            return success_response

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("src.brain.planner.genai.Client", FakeClient)

    planner = HostedLLMPlanner(
        api_key="fake", model="gemini-3.5-flash-lite", rate_limit_max_backoff_seconds=10.0
    )
    planner.next_step("do it", {}, [])
    assert slept_for == [10.0]  # capped at 10s, not the server's suggested 45s


def test_hosted_planner_defaults_are_faster_failing_than_original(monkeypatch):
    """Pins the new, safer defaults directly -- regression protection
    against silently reverting to the original 3-attempt/uncapped
    behavior that caused the 10+ minute live-run wait."""
    planner = HostedLLMPlanner(api_key="fake", model="gemini-3.5-flash-lite")
    assert planner._rate_limit_max_attempts == 2
    assert planner._rate_limit_max_backoff_seconds == 20.0


def test_hosted_planner_does_not_retry_non_rate_limit_api_errors(monkeypatch):
    """An auth failure or a real server error must never be silently
    retried the same way a 429 is -- only rate limits get the backoff
    treatment."""
    from google.genai import errors as genai_errors

    call_count = {"n": 0}

    class FakeModels:
        def generate_content(self, **kwargs):
            call_count["n"] += 1
            raise genai_errors.ClientError(401, {"error": {"message": "bad API key"}}, None)

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("src.brain.planner.genai.Client", FakeClient)

    planner = HostedLLMPlanner(api_key="fake", model="gemini-3.5-flash-lite")
    with pytest.raises(genai_errors.ClientError):
        planner.next_step("do it", {}, [])
    assert call_count["n"] == 1  # no retry at all for a non-429 error


def test_hosted_planner_generate_fn_reusable_for_risk_judge(monkeypatch):
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

    planner = HostedLLMPlanner(api_key="fake", model="gemini-3.5-flash-lite")
    raw = planner._generate_fn("system prompt", "user content")
    assert json.loads(raw)["risk"] == "destructive"
