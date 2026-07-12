import json

from src.brain.risk_classifier import Risk
from src.brain.risk_llm_judge import build_llm_risk_judge


def _fake_generate(risk_str):
    def _gen(system_prompt, user_content):
        return json.dumps({"risk": risk_str, "reason": "test"})
    return _gen


def test_judge_escalates_to_external():
    judge = build_llm_risk_judge(_fake_generate("external"))
    result = judge({"action": "click", "description": "make it go away permanently"})
    assert result == Risk.EXTERNAL


def test_judge_escalates_to_destructive():
    judge = build_llm_risk_judge(_fake_generate("destructive"))
    result = judge({"action": "click", "description": "get rid of this for good"})
    assert result == Risk.DESTRUCTIVE


def test_judge_returns_local_as_local():
    judge = build_llm_risk_judge(_fake_generate("local"))
    result = judge({"action": "scroll", "description": "scroll down"})
    assert result == Risk.LOCAL


def test_judge_fails_safe_on_bad_json():
    def _gen(system_prompt, user_content):
        return "not json at all"

    judge = build_llm_risk_judge(_gen)
    assert judge({"action": "click", "description": "x"}) is None


def test_judge_fails_safe_on_exception():
    def _gen(system_prompt, user_content):
        raise RuntimeError("network down")

    judge = build_llm_risk_judge(_gen)
    assert judge({"action": "click", "description": "x"}) is None


def test_judge_returns_none_for_unrecognized_risk_string():
    judge = build_llm_risk_judge(_fake_generate("maybe"))
    assert judge({"action": "click", "description": "x"}) is None
