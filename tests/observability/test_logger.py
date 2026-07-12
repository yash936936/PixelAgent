import json

from src.brain.risk_classifier import Risk
from src.confirmation.gate import GateDecision
from src.observability.logger import Logger, _redact_step


def _read_lines(logger):
    with open(logger.log_path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_redact_step_masks_password_field():
    step = {"action": "type", "description": "log in", "params": {"selector": "#pw", "password": "hunter2"}}
    redacted = _redact_step(step)
    assert redacted["params"]["password"] == "[REDACTED]"
    assert redacted["params"]["selector"] == "#pw"
    # Original is untouched
    assert step["params"]["password"] == "hunter2"


def test_redact_step_masks_various_credential_key_names():
    step = {
        "action": "type",
        "params": {
            "api_key": "sk-123", "secret": "s", "token": "t", "auth_header": "a",
            "credit_card_number": "4111", "cvv": "123", "ssn": "000-00-0000",
        },
    }
    redacted = _redact_step(step)
    for key in step["params"]:
        assert redacted["params"][key] == "[REDACTED]"


def test_redact_step_leaves_non_sensitive_params_untouched():
    step = {"action": "navigate", "params": {"url": "https://example.com"}}
    redacted = _redact_step(step)
    assert redacted["params"]["url"] == "https://example.com"


def test_redact_step_handles_missing_params():
    step = {"action": "done", "description": "finished"}
    assert _redact_step(step) == step


def test_redact_step_handles_non_dict_input():
    assert _redact_step(None) is None
    assert _redact_step("not a dict") == "not a dict"


def test_log_step_writes_redacted_password_to_disk(tmp_path):
    logger = Logger(log_dir=tmp_path)
    step = {"action": "type", "description": "log in", "params": {"password": "hunter2"}}
    logger.log_step(1, step, {"status": "ok"}, risk=Risk.LOCAL)

    records = _read_lines(logger)
    assert records[0]["step"]["params"]["password"] == "[REDACTED]"
    # Also confirm the raw file bytes never contain the plaintext secret.
    raw = logger.log_path.read_text(encoding="utf-8")
    assert "hunter2" not in raw


def test_log_gate_decision_redacts_step(tmp_path):
    logger = Logger(log_dir=tmp_path)
    step = {"action": "type", "params": {"secret": "shh"}}
    logger.log_gate_decision(1, step, Risk.EXTERNAL, GateDecision(verdict="approved"))

    raw = logger.log_path.read_text(encoding="utf-8")
    assert "shh" not in raw


def test_log_event_redacts_embedded_step(tmp_path):
    logger = Logger(log_dir=tmp_path)
    logger.log_event(1, {"status": "hard_boundary_blocked", "step": {"params": {"token": "abc123"}}})

    raw = logger.log_path.read_text(encoding="utf-8")
    assert "abc123" not in raw
