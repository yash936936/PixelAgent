import os

import pytest

from src import config


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in (
        "GEMINI_API_KEY", "LLM_MODEL", "PLANNER_BACKEND", "LOCAL_PLANNER_ENDPOINT",
        "RISK_MODEL_BACKEND", "LOCAL_RISK_MODEL_ENDPOINT", "TESSERACT_CMD", "AUTO_APPROVE_EXTERNAL",
        "RATE_LIMIT_MAX_ATTEMPTS", "RATE_LIMIT_MAX_BACKOFF_SECONDS", "LOG_RETENTION_DAYS", "EXECUTION_MODE",
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
    """Also patches credential_store.get_api_key() to None (2026-08-26):
    confirmed live on real Windows hardware that this failed with "DID
    NOT RAISE" once config.load() gained its Credential Manager fallback
    -- a real Windows Credential Manager is a second possible key source
    this test wasn't accounting for. See the equivalent fix/comment in
    tests/test_doctor.py's test_check_config_fails_without_api_key for
    the full explanation."""
    import src.security.credential_store as credential_store_module

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(credential_store_module, "get_api_key", lambda: None)
    with pytest.raises(RuntimeError):
        config.load(env_path=str(tmp_path / "does_not_exist.env"))


def test_default_risk_model_backend_is_none(tmp_path, monkeypatch):
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.risk_model_backend == "none"


def test_default_tesseract_cmd_is_none(tmp_path, monkeypatch):
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.tesseract_cmd is None


def test_tesseract_cmd_is_loaded_when_set(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.tesseract_cmd == r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def test_default_auto_approve_external_is_false(tmp_path, monkeypatch):
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.auto_approve_external is False


def test_auto_approve_external_true_is_parsed(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTO_APPROVE_EXTERNAL", "true")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.auto_approve_external is True


def test_auto_approve_external_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTO_APPROVE_EXTERNAL", "TRUE")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.auto_approve_external is True


def test_default_rate_limit_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.rate_limit_max_attempts == 2
    assert cfg.rate_limit_max_backoff_seconds == 20.0


def test_rate_limit_max_attempts_is_parsed(tmp_path, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_MAX_ATTEMPTS", "1")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.rate_limit_max_attempts == 1


def test_rate_limit_max_backoff_seconds_none_disables_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_MAX_BACKOFF_SECONDS", "none")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.rate_limit_max_backoff_seconds is None


def test_default_log_retention_days(tmp_path, monkeypatch):
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.log_retention_days == 14


def test_default_execution_mode_is_full_desktop(tmp_path, monkeypatch):
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.execution_mode == "full_desktop"


def test_execution_mode_browser_only_is_accepted(tmp_path, monkeypatch):
    monkeypatch.setenv("EXECUTION_MODE", "browser_only")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.execution_mode == "browser_only"


def test_execution_mode_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setenv("EXECUTION_MODE", "BROWSER_ONLY")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.execution_mode == "browser_only"


def test_invalid_execution_mode_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("EXECUTION_MODE", "something_else")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    with pytest.raises(RuntimeError, match="EXECUTION_MODE"):
        config.load(env_path=str(tmp_path / "does_not_exist.env"))


def test_log_retention_days_is_parsed(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_RETENTION_DAYS", "30")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    cfg = config.load(env_path=str(tmp_path / "does_not_exist.env"))
    assert cfg.log_retention_days == 30


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
