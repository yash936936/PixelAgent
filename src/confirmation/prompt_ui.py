"""
Minimal CLI/console confirmation prompt for Phase 1, matching the layout
specified in docs/DESIGN.md. Shows the proposed action, screenshot path (if
any), target account/profile, and Approve/Deny/Edit options.

Fix for a gap flagged in review: this function previously never actually
printed a screenshot path or account/profile at all, despite PHASES.md
always specifying that it should -- gate.py's prompt_fn signature simply
never carried that information. Now accepts an optional GateContext (see
gate.py) and prints both fields when present, falling back to "not
available" rather than silently omitting the line, so it's visibly obvious
in the CLI when that context wasn't supplied instead of just absent.
"""
from __future__ import annotations

from src.brain.risk_classifier import Risk
from src.confirmation.gate import GateContext, GateDecision

_HEADER = {
    Risk.EXTERNAL: "EXTERNAL ACTION — APPROVAL NEEDED",
    Risk.DESTRUCTIVE: "DESTRUCTIVE ACTION — APPROVAL + CONFIRM PHRASE NEEDED",
}


def console_prompt(step: dict, risk: Risk, context: GateContext | None = None) -> GateDecision:
    """Fix for a real, serious bug found live on 2026-08-01 (docs/DECISIONS.md):
    this function previously only explicitly checked for choice == "d" and
    choice == "e" -- ANY other input at all (a typo, a blank Enter, a
    completely unrelated string) silently fell through to a bare `# default
    / "a"` comment and was treated as APPROVED. This is the least safe
    possible default for a gate whose entire purpose is deliberate human
    approval before a risky/external/destructive action -- the whole
    project's safety model (risk_classifier.py, boundary_guard.py) is built
    on the assumption that this gate only approves on a genuine, intentional
    approval, not on "the user typed something, anything, at all."

    Now loops and re-prompts on any input that isn't recognized as
    approve/deny/edit, rather than ever silently defaulting to approved.
    Blank input (bare Enter) is also treated as unrecognized, not as an
    implicit approve -- the design in docs/DESIGN.md never marked any
    option as a default, so there's no legitimate reading of "no input" as
    "yes, approve.\""""
    context = context or GateContext()
    header = _HEADER.get(risk, "ACTION — APPROVAL NEEDED")
    print("┌─ " + header + " " + "─" * max(1, 60 - len(header)))
    print(f"│ Action: {step.get('description', step.get('action'))}")
    print(f"│ Raw action: {step.get('action')} params={step.get('params', {})}")
    print(f"│ Screenshot: {context.screenshot_path or 'not available'}")
    print(f"│ Account/profile: {context.account_profile or 'not available'}")
    print("│")
    print("│ [A]pprove   [D]eny   [E]dit and approve")
    print("└" + "─" * 62)

    while True:
        choice = input("> ").strip().lower()

        if choice in ("d", "deny"):
            return GateDecision(verdict="denied")

        if choice in ("e", "edit"):
            new_description = input("New description (blank to keep current): ").strip()
            edited = dict(step)
            if new_description:
                edited["description"] = new_description
            confirm_phrase = None
            if risk == Risk.DESTRUCTIVE:
                confirm_phrase = input('Type "CONFIRM" to proceed: ').strip()
            return GateDecision(verdict="approved", edited_step=edited, raw_user_input=confirm_phrase)

        if choice in ("a", "approve"):
            confirm_phrase = None
            if risk == Risk.DESTRUCTIVE:
                confirm_phrase = input('Type "CONFIRM" to proceed: ').strip()
            return GateDecision(verdict="approved", raw_user_input=confirm_phrase)

        print(f"Unrecognized input {choice!r} -- please enter A (approve), D (deny), or E (edit).")
