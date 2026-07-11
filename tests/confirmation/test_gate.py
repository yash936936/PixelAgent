from src.brain.risk_classifier import Risk
from src.confirmation.gate import ConfirmationGate, GateDecision


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
