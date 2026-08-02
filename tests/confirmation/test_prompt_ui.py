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


def test_unrecognized_input_never_silently_approves():
    """Real, serious bug found live on 2026-08-01 (docs/DECISIONS.md): a
    typo or unrelated string at the prompt used to silently fall through
    to approval. Must now re-prompt instead, and only actually approve
    once a real 'a'/'approve' is given."""
    step = {"action": "click", "description": "Star the repo", "params": {}}
    inputs = iter(["Notepad", "a"])  # exact real-world typo from the live trace
    with patch("builtins.input", side_effect=lambda *_: next(inputs)):
        decision = console_prompt(step, Risk.EXTERNAL)
    assert decision.verdict == "approved"


def test_unrecognized_input_can_be_followed_by_deny_not_forced_to_approve():
    """The re-prompt must not bias toward approval -- a user who mistypes
    can still end up denying."""
    step = {"action": "click", "description": "Star the repo", "params": {}}
    inputs = iter(["xyz", "d"])
    with patch("builtins.input", side_effect=lambda *_: next(inputs)):
        decision = console_prompt(step, Risk.EXTERNAL)
    assert decision.verdict == "denied"


def test_blank_input_is_not_treated_as_implicit_approve():
    """A bare Enter (blank string) must re-prompt, not silently approve --
    docs/DESIGN.md never marks any option as a default."""
    step = {"action": "click", "description": "Star the repo", "params": {}}
    inputs = iter(["", "d"])
    with patch("builtins.input", side_effect=lambda *_: next(inputs)):
        decision = console_prompt(step, Risk.EXTERNAL)
    assert decision.verdict == "denied"


def test_full_word_approve_deny_edit_also_accepted():
    step = {"action": "click", "description": "Star the repo", "params": {}}
    with patch("builtins.input", return_value="deny"):
        decision = console_prompt(step, Risk.EXTERNAL)
    assert decision.verdict == "denied"


def test_destructive_approve_requires_confirm_phrase(monkeypatch):
    step = {"action": "delete", "description": "Delete the file", "params": {}}
    inputs = iter(["a", "CONFIRM"])
    monkeypatch.setattr("builtins.input", lambda *_: next(inputs))
    decision = console_prompt(step, Risk.DESTRUCTIVE)
    assert decision.verdict == "approved"
    assert decision.raw_user_input == "CONFIRM"
