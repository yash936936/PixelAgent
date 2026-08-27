"""
Tests for src/observability/stress_runner.py's --real mode plumbing.

Deliberately does NOT make real Gemini/Chromium calls -- HostedLLMPlanner's
and PlaywrightDriver's constructors are both lazy (confirmed by reading their
source before writing these tests: genai.Client(api_key=...) doesn't call out
over the network at construction time, and PlaywrightDriver doesn't launch a
browser until _ensure_launched()/__enter__() is actually called), so these
tests can safely construct the real classes with a fake key/profile and check
wiring -- gate uses the deny-all prompt_fn, headless is threaded through
correctly, config.load() is actually invoked and its absence surfaces a clear
error -- without ever touching a real API or opening a real window.

The smoke-test (fakes) path is already covered by
tests/brain/test_orchestrator_stress.py; this file covers only what's new
for --real.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.confirmation.gate import GateDecision
from src.observability.operational_limits import TaskConcurrencyGuard
from src.observability.stress_runner import (
    _REAL_MODE_INSTRUCTION,
    _build_real_stress_orchestrator,
    _deny_all_prompt_fn,
    run_stress,
)


class TestDenyAllPromptFn:
    def test_always_returns_denied(self):
        decision = _deny_all_prompt_fn({"action": "click"}, "external", None)
        assert isinstance(decision, GateDecision)
        assert decision.verdict == "denied"

    def test_never_raises_regardless_of_risk_or_context(self):
        for risk in ["local", "external", "destructive", None, "anything"]:
            decision = _deny_all_prompt_fn({"action": "type", "params": {}}, risk, {"some": "context"})
            assert decision.verdict == "denied"

    def test_denial_reason_identifies_itself_as_the_stress_runner(self):
        decision = _deny_all_prompt_fn({"action": "click"}, "external", None)
        assert "stress_runner" in decision.raw_user_input


class TestRealModeInstruction:
    def test_instruction_is_explicitly_restrictive(self):
        lowered = _REAL_MODE_INSTRUCTION.lower()
        assert "do not" in lowered
        assert "click" in lowered
        assert "screenshot" in lowered or "describe" in lowered


class TestBuildRealStressOrchestrator:
    def _fake_cfg(self):
        cfg = MagicMock()
        cfg.gemini_api_key = "fake-key-not-real"  # pragma: allowlist secret
        cfg.llm_model = "gemini-3.5-flash-lite"
        cfg.rate_limit_max_attempts = 3
        cfg.rate_limit_max_backoff_seconds = 30.0
        cfg.default_chrome_profile = "default"
        cfg.profiles_dir = "/tmp/fake_profiles"
        cfg.max_steps_per_task = 5
        cfg.max_cost_usd = 0.10
        cfg.max_wall_clock_seconds = 60.0
        cfg.max_concurrent_tasks = 1
        return cfg

    def test_returns_a_driver_and_an_orchestrator(self, tmp_path):
        cfg = self._fake_cfg()
        guard = TaskConcurrencyGuard(max_concurrent=1)
        driver, orch = _build_real_stress_orchestrator(cfg, tmp_path, guard, headless=True)
        assert driver is not None
        assert orch is not None

    def test_driver_headless_flag_is_threaded_through(self, tmp_path):
        cfg = self._fake_cfg()
        guard = TaskConcurrencyGuard(max_concurrent=1)
        driver_headless, _ = _build_real_stress_orchestrator(cfg, tmp_path, guard, headless=True)
        driver_visible, _ = _build_real_stress_orchestrator(cfg, tmp_path, guard, headless=False)
        assert driver_headless._headless is True
        assert driver_visible._headless is False

    def test_gate_uses_deny_all_prompt_fn_not_console_prompt(self, tmp_path):
        cfg = self._fake_cfg()
        guard = TaskConcurrencyGuard(max_concurrent=1)
        _, orch = _build_real_stress_orchestrator(cfg, tmp_path, guard, headless=True)
        assert orch._gate._prompt_fn is _deny_all_prompt_fn

    def test_gate_never_auto_approves_external(self, tmp_path):
        cfg = self._fake_cfg()
        guard = TaskConcurrencyGuard(max_concurrent=1)
        _, orch = _build_real_stress_orchestrator(cfg, tmp_path, guard, headless=True)
        assert orch._gate._auto_approve_external is False

    def test_operational_limits_come_from_real_config_not_hardcoded(self, tmp_path):
        cfg = self._fake_cfg()
        cfg.max_cost_usd = 1.23
        guard = TaskConcurrencyGuard(max_concurrent=1)
        _, orch = _build_real_stress_orchestrator(cfg, tmp_path, guard, headless=True)
        assert orch._operational_limits.max_cost_usd == 1.23

    def test_concurrency_guard_is_the_shared_one_passed_in(self, tmp_path):
        cfg = self._fake_cfg()
        guard = TaskConcurrencyGuard(max_concurrent=1)
        _, orch = _build_real_stress_orchestrator(cfg, tmp_path, guard, headless=True)
        assert orch._concurrency_guard is guard


class TestRunStressRealModeRequiresConfig:
    def test_real_true_without_gemini_api_key_raises_clear_error(self, tmp_path, monkeypatch):
        """Confirms --real fails loudly and clearly when there's no real
        .env/GEMINI_API_KEY.

        Also patches credential_store.get_api_key() to None (added
        2026-08-26): confirmed live on real Windows hardware that this
        test failed with "DID NOT RAISE" once config.load() gained its
        Credential Manager fallback -- a real machine's real Credential
        Manager is a second possible source of a real key this test
        wasn't accounting for. This mock makes the test's actual intent
        (no key anywhere) explicit and machine-independent again."""
        import src.config as config_module
        import src.security.credential_store as credential_store_module

        monkeypatch.setattr(config_module, "load_dotenv", lambda *a, **kw: None)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setattr(credential_store_module, "get_api_key", lambda: None)

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            run_stress(tmp_path, iterations=1, real=True)

    def test_smoke_test_mode_never_calls_config_load(self, tmp_path):
        with patch("src.config.load") as mock_load:
            run_stress(tmp_path, iterations=2, real=False)
            mock_load.assert_not_called()
