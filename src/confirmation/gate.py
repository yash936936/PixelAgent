"""
Given a classified step, blocks execution for External/Destructive until an
approval decision is received, and records the decision. This is the module
docs/DEBUG.md says must be traced to prove an unapproved External/Destructive
step can never structurally reach action_router.py.

Fix for a gap flagged in review: PHASES.md Part 1.4 always specified that
the confirmation prompt shows "the proposed action, screenshot path, target
account/profile, and Approve/Deny/Edit options" -- but prompt_fn's signature
only ever received (step, risk), so no implementation of prompt_fn could
ever have shown a screenshot path or profile even if it wanted to. The gate
now optionally carries that context and passes it through, so
prompt_ui.console_prompt (and any future GUI) can actually display what the
docs always said it would.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from src.brain.risk_classifier import Risk

Verdict = Literal["approved", "denied"]


@dataclass
class GateContext:
    """Optional extra context for the prompt, beyond the step/risk
    themselves. All fields are optional -- callers that don't have a
    screenshot or profile handy (e.g. most existing unit tests) can omit
    this entirely and get identical behavior to before this fix."""

    screenshot_path: str | None = None
    account_profile: str | None = None


@dataclass
class GateDecision:
    verdict: Verdict
    edited_step: dict | None = None
    raw_user_input: str | None = None


class ConfirmationGate:
    """prompt_fn is injected so the gate has no direct UI dependency — Phase 1
    uses the console prompt_ui.py, a future GUI can supply a different
    callable with the same signature.

    auto_approve_external (2026-08-01, docs/DECISIONS.md): added per an
    explicit user request after finding that approving in a terminal
    window steals OS focus away from the actual target app (browser/
    Notepad), which then goes to the background and can cause the next
    step to act on the wrong window. When enabled, EXTERNAL-risk steps are
    approved immediately with NO prompt shown at all -- not just a fast
    default answer, the prompt_fn is never even called, so there is no
    approve-in-the-terminal focus-steal to cause the problem in the first
    place. Deliberately does NOT apply to Risk.DESTRUCTIVE regardless of
    this setting -- that tier's extra typed-CONFIRM-phrase requirement is
    this project's one genuinely non-negotiable human-in-the-loop gate,
    the same way boundary_guard.py's hard boundaries can't be disabled by
    any config value, and a convenience flag for reducing interruptions is
    not sufficient reason to remove the one gate specifically designed to
    require deliberate, hard-to-fat-finger confirmation."""

    def __init__(
        self,
        prompt_fn: Callable[[dict, Risk, GateContext], GateDecision],
        auto_approve_external: bool = False,
    ) -> None:
        self._prompt_fn = prompt_fn
        self._auto_approve_external = auto_approve_external

    def request_approval(
        self, step: dict, risk: Risk, context: GateContext | None = None
    ) -> GateDecision:
        if risk == Risk.LOCAL:
            # Local/reversible steps never reach the gate at all — enforced
            # by the orchestrator's needs_confirmation() check upstream, but
            # guarded here too so this module can never be called with a
            # Local step and silently approve it.
            return GateDecision(verdict="approved")

        if risk == Risk.EXTERNAL and self._auto_approve_external:
            return GateDecision(verdict="approved")

        decision = self._call_prompt(step, risk, context or GateContext())

        if risk == Risk.DESTRUCTIVE and decision.verdict == "approved":
            if decision.raw_user_input != "CONFIRM":
                # Destructive steps require the extra re-typed confirmation
                # phrase per docs/DESIGN.md — if it's missing, treat as denied
                # rather than silently downgrading the requirement.
                return GateDecision(verdict="denied")

        return decision

    def _call_prompt(self, step: dict, risk: Risk, context: GateContext) -> GateDecision:
        """Calls prompt_fn with the extra GateContext arg, but falls back to
        a two-arg call for any prompt_fn written against the old (step,
        risk) signature (e.g. any external/test callable that hasn't been
        updated) -- so this fix doesn't break existing callers."""
        try:
            return self._prompt_fn(step, risk, context)
        except TypeError:
            return self._prompt_fn(step, risk)
