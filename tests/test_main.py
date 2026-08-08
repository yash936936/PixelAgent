from dataclasses import dataclass
from unittest.mock import patch

import pytest

from src.brain.risk_classifier import Risk
from src.main import _build_desktop_backends, _build_risk_model_judge


@dataclass
class _FakeCfg:
    risk_model_backend: str = "none"
    local_risk_model_endpoint: str | None = None
    gemini_api_key: str = "fake-key"
    llm_model: str = "gemini-2.5-flash"
    execution_mode: str = "full_desktop"
    tesseract_cmd: str | None = None


def test_none_backend_returns_no_judge():
    cfg = _FakeCfg(risk_model_backend="none")
    assert _build_risk_model_judge(cfg) is None


def test_semantic_backend_builds_a_working_judge_with_no_endpoint_needed():
    """Phase 6 (2026-08-01): unlike 'hosted'/'local', 'semantic' needs no
    network/GPU/endpoint config at all -- it's in-process. Confirms the
    branch actually returns a working judge, not just that it doesn't
    raise."""
    cfg = _FakeCfg(risk_model_backend="semantic", local_risk_model_endpoint=None)
    judge = _build_risk_model_judge(cfg)
    assert judge is not None
    result = judge({"action": "click", "description": "get rid of this permanently"})
    assert result == Risk.DESTRUCTIVE


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


def test_build_desktop_backends_skips_mouse_keyboard_when_browser_only(capsys):
    """Real fix, docs/DECISIONS.md 2026-08-02, Phase 12: EXECUTION_MODE=
    browser_only must skip even attempting to construct MouseKeyboard
    (never call it at all), not just catch the resulting failure -- this
    is what the Docker image relies on for a clean, expected startup
    message instead of a generic 'unavailable' warning."""
    cfg = _FakeCfg(execution_mode="browser_only")
    with patch("src.main.MouseKeyboard") as mock_mk:
        mouse_keyboard, ocr_engine = _build_desktop_backends(cfg)

    mock_mk.assert_not_called()
    assert mouse_keyboard is None
    assert ocr_engine is not None
    captured = capsys.readouterr()
    assert "EXECUTION_MODE=browser_only" in captured.out


def test_build_desktop_backends_attempts_mouse_keyboard_when_full_desktop():
    cfg = _FakeCfg(execution_mode="full_desktop")
    with patch("src.main.MouseKeyboard") as mock_mk:
        mouse_keyboard, ocr_engine = _build_desktop_backends(cfg)

    mock_mk.assert_called_once()
    assert mouse_keyboard is mock_mk.return_value


def test_build_desktop_backends_degrades_gracefully_on_construction_failure():
    """Unchanged prior behavior for full_desktop mode: a real construction
    failure (e.g. genuinely no display) still degrades to web-only with a
    warning, distinct from the explicit browser_only skip above."""
    cfg = _FakeCfg(execution_mode="full_desktop")
    with patch("src.main.MouseKeyboard", side_effect=RuntimeError("no display")):
        mouse_keyboard, ocr_engine = _build_desktop_backends(cfg)

    assert mouse_keyboard is None
