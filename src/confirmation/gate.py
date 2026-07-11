"""
Given a classified step, blocks execution for External/Destructive until an
approval decision is received, and records the decision. This is the module
docs/DEBUG.md says must be traced to prove an unapproved External/Destructive
step can never structurally reach action_router.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from src.brain.risk_classifier import Risk

Verdict = Literal["approved", "denied"]


@dataclass
class GateDecision:
    verdict: Verdict
    edited_step: dict | None = None
    raw_user_input: str | None = None


class ConfirmationGate:
    """prompt_fn is injected so the gate has no direct UI dependency — Phase 1
    uses the console prompt_ui.py, a future GUI can supply a different
    callable with the same signature."""

    def __init__(self, prompt_fn: Callable[[dict, Risk], GateDecision]) -> None:
        self._prompt_fn = prompt_fn

    def request_approval(self, step: dict, risk: Risk) -> GateDecision:
        if risk == Risk.LOCAL:
            # Local/reversible steps never reach the gate at all — enforced
            # by the orchestrator's needs_confirmation() check upstream, but
            # guarded here too so this module can never be called with a
            # Local step and silently approve it.
            return GateDecision(verdict="approved")

        decision = self._prompt_fn(step, risk)

        if risk == Risk.DESTRUCTIVE and decision.verdict == "approved":
            if decision.raw_user_input != "CONFIRM":
                # Destructive steps require the extra re-typed confirmation
                # phrase per docs/DESIGN.md — if it's missing, treat as denied
                # rather than silently downgrading the requirement.
                return GateDecision(verdict="denied")

        return decision
