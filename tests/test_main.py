from dataclasses import dataclass

import pytest

from src.brain.risk_classifier import Risk
from src.main import _build_risk_model_judge


@dataclass
class _FakeCfg:
    risk_model_backend: str = "none"
    local_risk_model_endpoint: str | None = None
    gemini_api_key: str = "fake-key"
    llm_model: str = "gemini-2.5-flash"


def test_none_backend_returns_no_judge():
    cfg = _FakeCfg(risk_model_backend="none")
    assert _build_risk_model_judge(cfg) is None


def test_local_backend_without_endpoint_raises():
    cfg = _FakeCfg(risk_model_backend="local", local_risk_model_endpoint=None)
    with pytest.raises(RuntimeError, match="LOCAL_RISK_MODEL_ENDPOINT"):
        _build_risk_model_judge(cfg)


def test_local_backend_with_endpoint_builds_a_working_judge(monkeypatch):
    import json

    def fake_http_generate_fn(endpoint):
        def _gen(system_prompt, user_content):
            return json.dumps({"risk": "destructive", "reason": "test"})
        return _gen

    monkeypatch.setattr("src.main.build_http_generate_fn", fake_http_generate_fn)

    cfg = _FakeCfg(risk_model_backend="local", local_risk_model_endpoint="http://localhost:9999")
    judge = _build_risk_model_judge(cfg)
    assert judge is not None
    assert judge({"action": "click", "description": "x"}) == Risk.DESTRUCTIVE


def test_hosted_backend_builds_a_working_judge(monkeypatch):
    import json

    class FakeResponse:
        text = json.dumps({"risk": "external", "reason": "test"})
        usage_metadata = None

    class FakeModels:
        def generate_content(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("src.brain.planner.genai.Client", FakeClient)

    cfg = _FakeCfg(risk_model_backend="hosted")
    judge = _build_risk_model_judge(cfg)
    assert judge is not None
    assert judge({"action": "click", "description": "x"}) == Risk.EXTERNAL
