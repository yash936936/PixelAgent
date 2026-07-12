from src.brain.risk_classifier import Risk
from src.confirmation.gate import ConfirmationGate, GateContext, GateDecision


def test_local_never_calls_prompt():
    calls = []

    def prompt_fn(step, risk):
        calls.append((step, risk))
        return GateDecision(verdict="approved")

    gate = ConfirmationGate(prompt_fn=prompt_fn)
    decision = gate.request_approval({"action": "navigate"}, Risk.LOCAL)

    assert decision.verdict == "approved"
    assert calls == []  # prompt must never fire for Local steps


def test_external_denied_stays_denied():
    gate = ConfirmationGate(prompt_fn=lambda step, risk: GateDecision(verdict="denied"))
    decision = gate.request_approval({"action": "click"}, Risk.EXTERNAL)
    assert decision.verdict == "denied"


def test_destructive_requires_confirm_phrase():
    # Approved but WITHOUT the "CONFIRM" phrase must be downgraded to denied.
    gate = ConfirmationGate(
        prompt_fn=lambda step, risk: GateDecision(verdict="approved", raw_user_input="")
    )
    decision = gate.request_approval({"action": "delete"}, Risk.DESTRUCTIVE)
    assert decision.verdict == "denied"


def test_destructive_with_correct_confirm_phrase_approved():
    gate = ConfirmationGate(
        prompt_fn=lambda step, risk: GateDecision(verdict="approved", raw_user_input="CONFIRM")
    )
    decision = gate.request_approval({"action": "delete"}, Risk.DESTRUCTIVE)
    assert decision.verdict == "approved"


# --- fix for gap: gate must actually pass screenshot/profile context -----

def test_context_is_passed_through_to_three_arg_prompt_fn():
    received = {}

    def prompt_fn(step, risk, context):
        received["context"] = context
        return GateDecision(verdict="approved")

    gate = ConfirmationGate(prompt_fn=prompt_fn)
    ctx = GateContext(screenshot_path="/tmp/shot.png", account_profile="Default")
    gate.request_approval({"action": "click"}, Risk.EXTERNAL, ctx)

    assert received["context"].screenshot_path == "/tmp/shot.png"
    assert received["context"].account_profile == "Default"


def test_missing_context_defaults_to_empty_gate_context():
    received = {}

    def prompt_fn(step, risk, context):
        received["context"] = context
        return GateDecision(verdict="approved")

    gate = ConfirmationGate(prompt_fn=prompt_fn)
    gate.request_approval({"action": "click"}, Risk.EXTERNAL)  # no context passed

    assert received["context"].screenshot_path is None
    assert received["context"].account_profile is None


def test_old_two_arg_prompt_fn_still_works():
    # Backward compatibility: a prompt_fn written before this fix, taking
    # only (step, risk), must still work without modification.
    gate = ConfirmationGate(prompt_fn=lambda step, risk: GateDecision(verdict="approved"))
    ctx = GateContext(screenshot_path="/tmp/shot.png")
    decision = gate.request_approval({"action": "click"}, Risk.EXTERNAL, ctx)
    assert decision.verdict == "approved"
