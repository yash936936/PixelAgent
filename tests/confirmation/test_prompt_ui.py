from unittest.mock import patch

from src.brain.risk_classifier import Risk
from src.confirmation.gate import GateContext
from src.confirmation.prompt_ui import console_prompt


def test_prints_screenshot_path_and_profile_when_provided(capsys):
    ctx = GateContext(screenshot_path="/tmp/shot.png", account_profile="Work")
    step = {"action": "click", "description": "Star the repo", "params": {}}
    with patch("builtins.input", return_value="a"):
        console_prompt(step, Risk.EXTERNAL, ctx)
    out = capsys.readouterr().out
    assert "/tmp/shot.png" in out
    assert "Work" in out


def test_prints_not_available_when_context_missing(capsys):
    step = {"action": "click", "description": "Star the repo", "params": {}}
    with patch("builtins.input", return_value="a"):
        console_prompt(step, Risk.EXTERNAL, None)
    out = capsys.readouterr().out
    assert "not available" in out


def test_deny_returns_denied():
    step = {"action": "click", "description": "Star the repo", "params": {}}
    with patch("builtins.input", return_value="d"):
        decision = console_prompt(step, Risk.EXTERNAL)
    assert decision.verdict == "denied"


def test_destructive_approve_requires_confirm_phrase(monkeypatch):
    step = {"action": "delete", "description": "Delete the file", "params": {}}
    inputs = iter(["a", "CONFIRM"])
    monkeypatch.setattr("builtins.input", lambda *_: next(inputs))
    decision = console_prompt(step, Risk.DESTRUCTIVE)
    assert decision.verdict == "approved"
    assert decision.raw_user_input == "CONFIRM"
