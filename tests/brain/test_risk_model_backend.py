import json

from src.brain.risk_classifier import Risk
from src.brain.risk_model_backend import (
    HostedRiskJudge,
    LocalFineTunedRiskModel,
    RiskModelBackend,
)


def _fake_generate(risk_str, raise_error=False):
    def _gen(system_prompt, user_content):
        if raise_error:
            raise RuntimeError("boom")
        return json.dumps({"risk": risk_str, "reason": "test"})
    return _gen


def test_hosted_risk_judge_is_a_risk_model_backend():
    judge = HostedRiskJudge(generate_fn=_fake_generate("external"))
    assert isinstance(judge, RiskModelBackend)
    assert judge.judge({"action": "click", "description": "x"}) == Risk.EXTERNAL


def test_local_fine_tuned_risk_model_is_a_separate_class_from_hosted():
    # Track B requires these to be genuinely separate models/classes, not
    # just different constructor args of the same class.
    assert LocalFineTunedRiskModel is not HostedRiskJudge
    assert issubclass(LocalFineTunedRiskModel, RiskModelBackend)
    assert issubclass(HostedRiskJudge, RiskModelBackend)


def test_local_fine_tuned_risk_model_destructive():
    model = LocalFineTunedRiskModel(generate_fn=_fake_generate("destructive"))
    result = model.judge({"action": "click", "description": "get rid of this forever"})
    assert result == Risk.DESTRUCTIVE


def test_local_fine_tuned_risk_model_fails_safe_on_exception():
    model = LocalFineTunedRiskModel(generate_fn=_fake_generate("external", raise_error=True))
    assert model.judge({"action": "click", "description": "x"}) is None


def test_hosted_risk_judge_fails_safe_on_bad_json():
    def gen(system_prompt, user_content):
        return "not json"

    judge = HostedRiskJudge(generate_fn=gen)
    assert judge.judge({"action": "click", "description": "x"}) is None


def test_risk_model_backend_is_abstract():
    import pytest

    with pytest.raises(TypeError):
        RiskModelBackend()  # cannot instantiate the interface directly
