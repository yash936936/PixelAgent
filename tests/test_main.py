import json

from src.brain.planner import LocalPlanner
from src.main import _build_llm_risk_judge


def test_build_llm_risk_judge_from_local_planner():
    def fake_generate(system_prompt, user_content):
        return json.dumps({"risk": "external", "reason": "test"})

    planner = LocalPlanner(generate_fn=fake_generate)
    judge = _build_llm_risk_judge(planner)
    assert judge is not None

    from src.brain.risk_classifier import Risk
    result = judge({"action": "click", "description": "do a thing"})
    assert result == Risk.EXTERNAL


def test_build_llm_risk_judge_returns_none_without_generate_fn():
    class NoGenerateFnPlanner:
        pass

    judge = _build_llm_risk_judge(NoGenerateFnPlanner())
    assert judge is None
