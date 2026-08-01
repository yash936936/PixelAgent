import os

import pytest

from src import config


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in (
        "GEMINI_API_KEY", "LLM_MODEL", "PLANNER_BACKEND", "LOCAL_PLANNER_ENDPOINT",
        "RISK_MODEL_BACKEND", "LOCAL_RISK_MODEL_ENDPOINT",
        "DEFAULT_CHROME_PROFILE", "PROFILES_DIR", "MAX_STEPS_PER_TASK", "LOG_DIR",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    yield


def test_default_planner_backend_is_hosted(tmp_path, monkeypatch):
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.planner_backend == "hosted"
    assert cfg.local_planner_endpoint is None


def test_planner_backend_local_is_accepted(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANNER_BACKEND", "local")
    monkeypatch.setenv("LOCAL_PLANNER_ENDPOINT", "http://localhost:11434/api/generate")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.planner_backend == "local"
    assert cfg.local_planner_endpoint == "http://localhost:11434/api/generate"


def test_invalid_planner_backend_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANNER_BACKEND", "quantum")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    with pytest.raises(RuntimeError):
        config.load(env_path=str(tmp_path / "does_not_exist.env"))


def test_missing_api_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        config.load(env_path=str(tmp_path / "does_not_exist.env"))


def test_default_risk_model_backend_is_none(tmp_path, monkeypatch):
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.risk_model_backend == "none"


def test_risk_model_backend_semantic_is_accepted_with_no_endpoint(tmp_path, monkeypatch):
    """Phase 6 (2026-08-01): 'semantic' needs no LOCAL_RISK_MODEL_ENDPOINT,
    unlike 'local' -- it's in-process, no network call."""
    monkeypatch.setenv("RISK_MODEL_BACKEND", "semantic")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.risk_model_backend == "semantic"
    assert cfg.local_risk_model_endpoint is None


def test_risk_model_backend_local_is_accepted(tmp_path, monkeypatch):
    monkeypatch.setenv("RISK_MODEL_BACKEND", "local")
    monkeypatch.setenv("LOCAL_RISK_MODEL_ENDPOINT", "http://localhost:11435/api/generate")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.risk_model_backend == "local"
    assert cfg.local_risk_model_endpoint == "http://localhost:11435/api/generate"


def test_invalid_risk_model_backend_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("RISK_MODEL_BACKEND", "quantum")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    with pytest.raises(RuntimeError, match="RISK_MODEL_BACKEND"):
        config.load(env_path=str(tmp_path / "does_not_exist.env"))
